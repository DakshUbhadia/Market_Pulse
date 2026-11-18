"""Find final quotations without dated lifecycle explanations; never infer recovery."""
from datetime import date
import json

import pandas as pd

from quant.data.security_history import instrument_id
from quant.pipeline.backfill_lifecycle import load_lifecycle
from quant.storage.duckdb_store import research_connection
from quant.storage.parquet_store import write_parquet
from quant.storage.research_store import write_json
from quant.universe.eligible import session_index

CLASSIFICATIONS = {
    'DELISTED': 'VERIFIED_DELISTING', 'VOLUNTARY_DELISTING': 'VERIFIED_DELISTING',
    'COMPULSORY_DELISTING': 'VERIFIED_DELISTING', 'SUSPENDED': 'VERIFIED_SUSPENSION',
    'SUSPENSION_ANNOUNCED': 'VERIFIED_SUSPENSION', 'SHARE_CONVERSION': 'VERIFIED_CONVERSION',
    'CASH_SETTLEMENT': 'VERIFIED_CASH_SETTLEMENT',
}


def audit_security_lifecycle_gaps(quotes, sessions, events, as_of, *, grace_sessions=5):
    """Quotes may be daily bars or one last_quoted_date row per stable identity.

    A grace period avoids calling the tail of an incomplete download a delisting.
    Classification explains a missing quote; suspension is not economic resolution.
    """
    if grace_sessions < 1:
        raise ValueError('grace_sessions must be positive')
    dates = session_index(sessions)
    dates = dates[dates <= pd.Timestamp(as_of)]
    if dates.empty:
        raise ValueError('No exchange sessions through as_of')
    columns = ['instrument_id', 'symbol', 'last_quoted_date', 'missing_sessions',
               'candidate_event', 'evidence_event_ids', 'economic_resolution_verified']
    if quotes.empty:
        return pd.DataFrame(columns=columns)
    frame = quotes.copy()
    if 'trade_date' in frame:
        frame = frame[pd.to_datetime(frame.trade_date).le(pd.Timestamp(as_of))]
        if 'volume' in frame:
            frame = frame[frame.volume.gt(0)]
        frame = frame.rename(columns={'trade_date': 'last_quoted_date'})
    frame = frame[pd.to_datetime(frame.last_quoted_date).le(pd.Timestamp(as_of))]
    frame = frame.dropna(subset=['instrument_id']).sort_values(['last_quoted_date', 'symbol'])
    frame = frame.drop_duplicates('instrument_id', keep='last')
    known = events.copy()
    if not known.empty:
        cutoff = pd.Timestamp(as_of).tz_localize('Asia/Kolkata') + pd.Timedelta(days=1)
        known = known[known.verification_status.eq('VERIFIED')
                      & pd.to_datetime(known.announced_at, utc=True).lt(cutoff)
                      & pd.to_datetime(known.effective_date).le(pd.Timestamp(as_of))]
    rows = []
    for row in frame.itertuples():
        last = pd.Timestamp(row.last_quoted_date)
        missing = int((dates > last).sum())
        if missing < grace_sessions:
            continue
        evidence = known[known.instrument_id.eq(row.instrument_id)
                         & pd.to_datetime(known.effective_date).ge(last)] if not known.empty else known
        if not evidence.empty:
            evidence = evidence[evidence.event_type.isin(CLASSIFICATIONS)].sort_values(['effective_date', 'announced_at'])
        economic = evidence[evidence.event_type.isin(['CASH_SETTLEMENT', 'SHARE_CONVERSION'])
                            & evidence.mandatory.eq(True) & evidence.optional.eq(False)] if not evidence.empty else evidence
        if not economic.empty:
            cash = economic.event_type.eq('CASH_SETTLEMENT')
            due = pd.to_datetime(economic.get('settlement_date', pd.Series(pd.NaT, index=economic.index)))
            economic = economic[~cash | due.le(pd.Timestamp(as_of))]
        # An optional tender or an undocumented payment never resolves economics.
        selected = economic.iloc[-1] if not economic.empty else (evidence.iloc[-1] if not evidence.empty else None)
        rows.append(dict(instrument_id=row.instrument_id, symbol=row.symbol, last_quoted_date=last,
            missing_sessions=missing, candidate_event=CLASSIFICATIONS[selected.event_type] if selected is not None else 'UNEXPLAINED_FINAL_QUOTE',
            evidence_event_ids=','.join(evidence.lifecycle_event_id) if not evidence.empty else '',
            economic_resolution_verified=not economic.empty))
    return pd.DataFrame(rows, columns=columns)


def load_last_quotes(config, as_of):
    """Aggregate raw observed ISINs across trading series, avoiding current masters."""
    with research_connection(config.data_dir) as connection:
        frame = connection.execute('''WITH observed AS (
            SELECT isin,symbol,series,trade_date FROM prices
            WHERE trade_date <= ? AND volume > 0 AND close > 0 AND isin LIKE 'INE%'),
            candidates AS (SELECT DISTINCT isin FROM observed WHERE series='EQ')
            SELECT isin,arg_max(symbol,trade_date) AS symbol,max(trade_date) AS last_quoted_date
            FROM observed JOIN candidates USING (isin) GROUP BY isin''', [as_of]).fetchdf()
    frame['instrument_id'] = frame['isin'].map(instrument_id)
    return frame


def run_audit(config, as_of, *, grace_sessions=5):
    from quant.storage.parquet_store import read_parquet_file
    calendar = read_parquet_file(config.calendar_path)
    sessions = calendar.loc[calendar.is_trading_session, 'trade_date']
    frame = audit_security_lifecycle_gaps(load_last_quotes(config, as_of), sessions,
                                         load_lifecycle(config), as_of, grace_sessions=grace_sessions)
    write_parquet(frame, config.data_dir/'reports/security-lifecycle-gaps.parquet')
    report = dict(as_of=str(as_of), grace_sessions=grace_sessions, coverage_status='UNESTABLISHED',
                  scope='IDENTITIES_OBSERVED_IN_EQ_BY_AS_OF; FINAL_QUOTES_ACROSS_ALL_SERIES',
                  anomalies=len(frame), classifications=frame.candidate_event.value_counts().to_dict())
    write_json(config.data_dir/'reports/security-lifecycle-gaps.json', report)
    return frame, report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat)
    parser.add_argument('--grace-sessions', type=int, default=5)
    args = parser.parse_args()
    _, report = run_audit(args.config(config), args.as_of or args.end, grace_sessions=args.grace_sessions)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
