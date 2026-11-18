"""Data-health gate: a current run cannot inherit readiness from a stale result."""
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

import numpy as np

from quant.data.http import atomic_write
from quant.data.source_registry import source_status
from quant.pipeline.audit_prices import audit_prices
from quant.pipeline.state import PipelineState
from quant.pipeline.update_calendar import read_calendar
from quant.boundaries import RAW_PRICE_START
from quant.storage.parquet_store import read_parquet_file


def validate_data(config, start, end, *, run_errors=None, incremental=False):
    state = PipelineState(config)
    now = datetime.now(ZoneInfo(config.timezone))
    sources = source_status(config, state.data, as_of=now.date())
    errors = dict(run_errors or {})
    from quant.pipeline.audit_lifecycle import audit_lifecycle
    lifecycle = audit_lifecycle(config,as_of=end,write=False)
    if lifecycle['status'] == 'BLOCKED':
        errors['lifecycle'] = '; '.join(lifecycle['errors']) or 'Unresolved held lifecycle evidence'
    sessions = set()
    freshness_as_of = None
    try:
        calendar = read_calendar(config, start, end)
        sessions = set(calendar.loc[calendar.is_trading_session, 'trade_date'].dt.date)
        if not calendar.loc[calendar.is_trading_session, 'verified'].all():
            raise ValueError('Calendar has sessions without validated price evidence')
        if sessions:
            # An after-close job may finish after midnight or on a nontrading
            # day. Freshness belongs to its latest completed exchange session.
            freshness_as_of = max(sessions)
            sources = source_status(config,state.data,as_of=freshness_as_of)
        sources['nse_calendar']['status'] = 'READY'
    except (OSError, ValueError, KeyError) as error:
        errors['calendar'] = str(error)
        sources['nse_calendar']['status'] = 'FAILED'
    try:
        audit = audit_prices(config, start, end)
        sources['nse_bhavcopy'].update(audit)
        sources['nse_bhavcopy']['status'] = 'READY' if audit['status'] == 'READY' else 'FAILED'
        if audit['missing_sessions'] and audit['missing_sessions'][-1] == str(end):
            sources['nse_bhavcopy']['status'] = 'FAILED'
    except (OSError, ValueError, KeyError) as error:
        audit = {'status': 'NOT_READY', 'error': str(error)}
        sources['nse_bhavcopy']['status'] = 'FAILED'
        errors['prices'] = str(error)
    from quant.pipeline.update_market_eod import daily_path
    for dataset, source in [('indices', 'nse_indices'), ('vix', 'nse_vix'), ('adjusted_prices', 'adjusted_prices')]:
        missing, invalid = [], []
        for day in sorted(sessions):
            path = daily_path(config, dataset, day)
            if not path.exists():
                missing.append(str(day))
                continue
            try:
                frame = read_parquet_file(path)
                if frame.empty or not pd.to_datetime(frame.trade_date).dt.date.eq(day).all():
                    raise ValueError('Missing rows or incorrect partition date')
                if dataset in ('indices', 'vix'):
                    from quant.data.normalization import keys
                    keys(frame, ['trade_date', 'index_name'] if dataset == 'indices' else ['trade_date'])
                    values = frame.close.to_numpy(dtype=float)
                    if not np.isfinite(values).all() or (values <= 0).any():
                        raise ValueError('Invalid benchmark close')
                    if dataset == 'indices' and day == max(sessions):
                        from quant.data.nse_indices import REQUIRED_INDICES
                        if not REQUIRED_INDICES.issubset(set(frame.index_name)):
                            raise ValueError('Required benchmark indices missing')
                    if dataset == 'indices' and 'data_quality' in frame:
                        from quant.data.nse_indices import REQUIRED_INDICES
                        core = frame[frame.index_name.isin(REQUIRED_INDICES)]
                        if core.data_quality.eq('INVALID_OHLC').any():
                            raise ValueError('Invalid required benchmark OHLC')
                else:
                    eligible = frame[frame.adjustment_status == 'OK']
                    if eligible.empty or eligible[['adjusted_close', 'total_return_close']].isna().any().any():
                        raise ValueError('No valid adjusted research prices')
            except (OSError, ValueError, KeyError, TypeError) as error:
                invalid.append({'date': str(day), 'error': str(error)})
        sources[source].update(missing_sessions=missing, invalid_partitions=invalid)
        if missing or invalid or not sessions:
            sources[source]['status'] = 'FAILED'
    master_day = now.date()
    try:
        master_day = date.fromisoformat(state.data.get('nse_security_master',{}).get('last_success',str(master_day)))
        if master_day > now.date():
            raise ValueError('Security-master acquisition date is in the future')
    except (ValueError,TypeError) as error:
        sources['nse_security_master'].update(status='FAILED',error=str(error))
        master_day = now.date()
    master = config.data_dir / 'normalized' / 'instruments' / 'nse' / f'{master_day}.parquet'
    identities = config.data_dir / 'normalized' / 'security_history' / 'identities.parquet'
    for source, path, required in [('nse_security_master', master, ['symbol', 'series', 'isin']),
                                   ('security_history', identities, ['symbol', 'series', 'identity_status'])]:
        try:
            frame = read_parquet_file(path, columns=required)
            if frame.empty:
                raise ValueError('Empty identity dataset')
        except (OSError, ValueError, KeyError) as error:
            sources[source].update(status='FAILED', error=str(error))
    corporate = state.data.get('nse_corporate_actions', {})
    if (corporate.get('checked_through', '') < str(end)
            or corporate.get('checked_from', '9999-12-31') > str(start)):
        sources['nse_corporate_actions']['status'] = 'STALE'
    excluded = []
    action_files = list((config.data_dir / 'normalized' / 'corporate_actions').rglob('*.parquet'))
    try:
        if action_files:
            actions = pd.concat([read_parquet_file(path) for path in action_files]).drop_duplicates('event_id')
            bad = actions[(~actions.parse_status.isin(['PARSED', 'NON_ADJUSTING']))
                          & (pd.to_datetime(actions.ex_date).dt.date <= end)]
            excluded = sorted(bad.symbol.dropna().unique().tolist())
    except (OSError, ValueError, KeyError) as error:
        sources['nse_corporate_actions']['status'] = 'FAILED'
        errors['corporate_actions'] = str(error)
    essential = [name for name, row in sources.items() if row.get('required')]
    historical_ready = start <= RAW_PRICE_START and audit['status'] == 'READY'
    if incremental:
        prior = state.data.get('weekly_integrity', {})
        historical_ready = prior.get('status') == 'READY' and prior.get('from') == str(RAW_PRICE_START)
        try:
            historical_ready = historical_ready and (pd.Timestamp(now)-pd.Timestamp(prior['last_successful_at'])).days <= 7
        except (ValueError, KeyError, TypeError):
            historical_ready = False
    elif start > RAW_PRICE_START:
        try:
            historical_ready = audit_prices(config, RAW_PRICE_START, end, write=False)['status'] == 'READY'
        except (OSError, ValueError, KeyError):
            historical_ready = False
    ready = (not errors and historical_ready and audit['status'] == 'READY'
             and all(sources[name]['status'] == 'READY' for name in essential))
    report = {
        'as_of': str(end), 'generated_at': now.isoformat(), 'status': 'READY' if ready else 'NOT_READY',
        'freshness_as_of': str(freshness_as_of) if freshness_as_of else None,
        'recommendation_allowed': False, 'publication_gate': 'DISABLED_RESEARCH_PHASE',
        'sources': sources, 'price_audit': audit,
        'lifecycle_health': lifecycle,
        'excluded_symbols': excluded, 'errors': errors,
        'full_history_ready': historical_ready,
        'fundamental_research_allowed': (ready and sources['nse_financials']['status'] == 'READY'
                                         and sources['nse_financials'].get('usable_filings', 0) > 0
                                         and not sources['nse_financials'].get('needs_review')),
        'policy': 'Preserve prior results and mark stale whenever essential data are incomplete.',
    }
    atomic_write(config.data_dir / 'reports' / f'data-health-{now:%Y-%m-%d}.json',
                 json.dumps(report, indent=2, default=str).encode())
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    args = parser.parse_args()
    report = validate_data(args.config(config), args.start, args.end)
    print(json.dumps({'as_of': report['as_of'], 'status': report['status'],
                      'recommendation_allowed': report['recommendation_allowed'],
                      'price_coverage_percent': report['price_audit'].get('coverage_percent'),
                      'excluded_symbol_count': len(report['excluded_symbols']),
                      'sources': {key: value['status'] for key, value in report['sources'].items()},
                      'errors': report['errors']}, indent=2))
    return 0 if report['status'] == 'READY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
