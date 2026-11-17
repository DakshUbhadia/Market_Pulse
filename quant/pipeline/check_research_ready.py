"""Fail-closed research gate; fundamentals and optional live feeds are irrelevant to V1."""
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from quant.data.http import atomic_write
from quant.pipeline.audit_prices import audit_prices
from quant.pipeline.update_calendar import read_calendar
from quant.pipeline.state import PipelineState
from quant.boundaries import RAW_PRICE_START, identity_boundary
from quant.universe.config import UniverseConfig


def check_research_ready(config, *, as_of=None, history_start=RAW_PRICE_START,
                         requested_backtest_start=None, min_history_sessions=None, write=True):
    from quant.pipeline.research_proof import fingerprint_inputs, save_readiness_proof
    from quant.pipeline.cli import completed_day
    target = as_of or completed_day(config)
    requested_start = requested_backtest_start or target
    minimum = UniverseConfig().min_history_sessions if min_history_sessions is None else min_history_sessions
    if requested_start > target:
        raise ValueError('Requested research start is after as_of')
    fingerprint = fingerprint_inputs(config,target) if write else None
    checks = dict(price_history_ready=False, calendar_ready=False, adjustments_ready=False,
                  index_history_ready=False, identity_ready=False, corporate_actions_ready=False)
    errors, excluded, unresolved_sessions = {}, set(), []
    coverage, latest = 0.0, None
    expected, resolved_sessions = [], []
    try:
        calendar = read_calendar(config, history_start, target)
        expected = sorted(calendar.loc[calendar.is_trading_session, 'trade_date'].dt.date)
        if not expected:
            raise ValueError('No expected sessions')
        latest = expected[-1]
        checks['calendar_ready'] = True
        audit = audit_prices(config, history_start, target, write=False)
        coverage = audit['coverage_percent'] / 100
        checks['price_history_ready'] = audit['status'] == 'READY' and audit['latest_date'] == str(latest)
        for dataset, check in [('adjusted_prices', 'adjustments_ready'), ('indices', 'index_history_ready')]:
            valid, bad, corrupt = 0, [], False
            for day in expected:
                path = config.data_dir / 'normalized' / dataset / f'year={day.year}/month={day.month:02d}/{day}.parquet'
                try:
                    frame = pd.read_parquet(path)
                    if frame.empty or not pd.to_datetime(frame.trade_date).dt.date.eq(day).all():
                        raise ValueError('Incorrect dataset date')
                    if dataset == 'indices':
                        for name in ('NIFTY 50', 'NIFTY 500'):
                            rows = frame[frame.index_name == name]
                            if len(rows) != 1 or not np.isfinite(rows.close.iloc[0]) or rows.close.iloc[0] <= 0:
                                raise ValueError(f'{name} missing or invalid')
                            bar = rows[['open','high','low','close']].iloc[0]
                            if (not np.isfinite(bar.to_numpy(dtype=float)).all() or (bar <= 0).any()
                                    or bar.high < bar.max() or bar.low > bar.min()):
                                raise ValueError(f'{name} invalid executable OHLC')
                            if 'data_quality' in rows and rows.data_quality.eq('INVALID_OHLC').any():
                                raise ValueError(f'{name} invalid OHLC')
                    else:
                        traded_EQ = frame[frame.series.eq('EQ') & frame.volume.gt(0)]
                        if traded_EQ.empty or not traded_EQ.instrument_id.notna().all():
                            unresolved_sessions.append(str(day))
                        else:
                            resolved_sessions.append(day)
                        if frame.duplicated(['trade_date', 'symbol', 'series']).any():
                            raise ValueError('Duplicate adjusted price keys')
                        # Bhavcopies retain nontraded securities with zero OHLC.
                        # They cannot execute; do not mistake them for corrupt
                        # traded EQ bars or invent opens for suspended names.
                        ok = frame[frame.adjustment_status.eq('OK') & frame.series.eq('EQ') & frame.volume.gt(0)]
                        fields = ['adjusted_open', 'adjusted_high', 'adjusted_low', 'adjusted_close']
                        unresolved_only = (not traded_EQ.empty and traded_EQ.instrument_id.isna().all()
                            and traded_EQ.adjustment_status.eq('UNRESOLVED_IDENTITY').all())
                        if (ok.empty and not unresolved_only) or not np.isfinite(ok[fields].to_numpy(dtype=float)).all() or (ok[fields] <= 0).any().any():
                            raise ValueError('Adjusted executable OHLC unavailable')
                        if ((ok.adjusted_high < ok[['adjusted_open', 'adjusted_close', 'adjusted_low']].max(axis=1))
                                | (ok.adjusted_low > ok[['adjusted_open', 'adjusted_close', 'adjusted_high']].min(axis=1))).any():
                            raise ValueError('Invalid adjusted OHLC')
                        excluded.update(frame.loc[frame.adjustment_status != 'OK', 'symbol'].dropna())
                        raw = pd.read_parquet(config.prices_dir / f'year={day.year}/month={day.month:02d}/{day}.parquet',
                                              columns=['trade_date', 'symbol', 'series', 'source_hash'])
                        merged = frame.merge(raw, on=['trade_date', 'symbol', 'series'], how='outer', indicator=True)
                        if not merged['_merge'].eq('both').all() or not merged.source_price_sha256.eq(merged.source_hash_y if 'source_hash_y' in merged else merged.source_hash).fillna(False).all():
                            raise ValueError('Adjusted price provenance differs from raw prices')
                    valid += 1
                except (OSError, ValueError, KeyError, TypeError) as error:
                    corrupt |= path.exists()
                    bad.append({'date': str(day), 'error': str(error)})
            checks[check] = not corrupt and valid / len(expected) >= .995 and not any(row['date'] == str(latest) for row in bad)
            if bad:
                errors[dataset] = bad
    except (OSError, ValueError, KeyError) as error:
        errors['calendar_or_prices'] = str(error)
    try:
        ids = pd.read_parquet(config.data_dir / 'normalized/security_history/identities.parquet')
        checks['identity_ready'] = (not ids.empty and (ids.identity_status == 'RESOLVED').any()
                                    and (ids.valid_from <= ids.valid_to).all())
    except (OSError, ValueError, KeyError) as error:
        errors['identity'] = str(error)
    boundary = identity_boundary(expected, resolved_sessions, requested_start, minimum)
    if not boundary['identity_ready_for_requested_window']:
        checks['identity_ready'] = False
    identity_diagnostics = None
    if unresolved_sessions:
        identity_diagnostics = dict(sessions_without_resolved_EQ=len(unresolved_sessions),
            first_date=unresolved_sessions[0], last_date=unresolved_sessions[-1],
            remediation='Load dated historical symbol/series/ISIN evidence; do not backfill from today\'s master')
        if not boundary['identity_ready_for_requested_window']:
            errors['historical_identity'] = identity_diagnostics
    state = PipelineState(config).data
    actions = state.get('nse_corporate_actions', {})
    checks['corporate_actions_ready'] = (actions.get('status') == 'READY'
        and actions.get('checked_from', '9999-12-31') <= str(history_start)
        and actions.get('checked_through', '') >= str(latest or target))
    adjusted = state.get('adjusted_prices', {})
    if (adjusted.get('status') != 'READY' or adjusted.get('from', '9999-12-31') > str(history_start)
            or adjusted.get('to', '') < str(latest or target)):
        checks['adjustments_ready'] = False
        errors['adjustment_range'] = 'Adjusted-price baseline does not cover the required history through the latest session'
    try:
        from quant.features.adjustments import action_version
        files = list((config.data_dir / 'normalized/corporate_actions').rglob('*.parquet'))
        actions_frame = pd.concat([pd.read_parquet(path) for path in files]).drop_duplicates('event_id') if files else pd.DataFrame()
        if not actions_frame.empty:
            # Stored adjustments are anchored to their build date. Future split
            # scaling cancels in historical returns and never supplies a signal.
            anchor = date.fromisoformat(adjusted.get('to', str(target)))
            actions_frame = actions_frame[pd.to_datetime(actions_frame.ex_date).dt.date <= anchor]
        if adjusted.get('corporate_action_version') != action_version(actions_frame):
            checks['adjustments_ready'] = False
            errors['adjustment_version'] = 'Corporate-action inputs changed; rebuild adjusted prices'
        if latest and not actions_frame.empty:
            unresolved = actions_frame[(~actions_frame.parse_status.isin(['PARSED','NON_ADJUSTING'])
                | (actions_frame.instrument_id.isna() & actions_frame.parse_status.ne('NON_ADJUSTING')))
                & (pd.to_datetime(actions_frame.ex_date).dt.date <= latest)]
            latest_prices = pd.read_parquet(config.data_dir / 'normalized/adjusted_prices' /
                f'year={latest.year}/month={latest.month:02d}/{latest}.parquet')
            for event in unresolved.itertuples():
                affected = (latest_prices.instrument_id.eq(event.instrument_id) if pd.notna(event.instrument_id)
                            else latest_prices.symbol.eq(event.symbol))
                if (affected & latest_prices.adjustment_status.eq('OK')).any():
                    checks['adjustments_ready'] = False
                    errors['unresolved_action_exclusion'] = 'Unresolved corporate-action identity is still executable'
                    break
    except (OSError, ValueError, KeyError) as error:
        checks['adjustments_ready'] = False
        errors['adjustment_version'] = str(error)
    checks = {name: bool(value) for name, value in checks.items()}
    from quant.pipeline.audit_lifecycle import audit_lifecycle
    lifecycle = audit_lifecycle(config,as_of=target,write=False)
    if lifecycle['status'] == 'BLOCKED':
        checks['lifecycle_evidence_integrity'] = False
        errors['lifecycle'] = lifecycle['errors']
    if write and fingerprint != fingerprint_inputs(config,target):
        checks['inputs_unchanged_during_audit'] = False
        errors['input_change'] = 'Research inputs or gate sources changed during the audit; repeat it'
    result = dict(status='READY' if all(checks.values()) else 'NOT_READY', **checks,
                  full_history_start=str(history_start), raw_price_start=audit.get('earliest_date', str(history_start)) if expected and 'audit' in locals() else None,
                  **boundary, latest_session=str(latest) if latest else None,
                  historical_identity_diagnostics=identity_diagnostics,
                  as_of=str(target), coverage=coverage, excluded_symbols=sorted(excluded), errors=errors,
                  lifecycle_data_ready=lifecycle['lifecycle_data_ready'],
                  lifecycle_coverage_start=lifecycle['lifecycle_coverage_start'],
                  unresolved_held_lifecycle_events=lifecycle['unresolved_held_lifecycle_events'],
                  production_research_ready=all(checks.values()) and lifecycle['lifecycle_data_ready'],
                  generated_at=datetime.now(ZoneInfo(config.timezone)).isoformat(), recommendations_allowed=False)
    if write:
        atomic_write(config.data_dir / 'reports/research-readiness.json', json.dumps(result, indent=2).encode())
        if history_start == RAW_PRICE_START:
            save_readiness_proof(config,result,fingerprint)
    return result


def require_research_ready(config, as_of, requested_backtest_start=None):
    from quant.pipeline.research_proof import cached_readiness
    requested_start = requested_backtest_start or as_of
    result = cached_readiness(config,as_of,requested_start,UniverseConfig().min_history_sessions)
    if result is not None:
        return result
    result = check_research_ready(config, as_of=as_of, requested_backtest_start=requested_backtest_start)
    if result['status'] != 'READY':
        raise ValueError('Research data NOT_READY; inspect data/reports/research-readiness.json')
    return result


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat)
    parser.add_argument('--backtest-start', type=date.fromisoformat)
    args = parser.parse_args()
    result = check_research_ready(args.config(config), as_of=args.as_of or args.end,
                                  requested_backtest_start=args.backtest_start)
    print(json.dumps({k: v for k, v in result.items() if k not in ('excluded_symbols', 'errors')}, indent=2))
    return 0 if result['status'] == 'READY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
