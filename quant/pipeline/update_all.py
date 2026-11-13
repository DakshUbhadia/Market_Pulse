"""Single scheduled refresh. Always write data health, including after failures."""
import json

from quant.pipeline.audit_prices import audit_prices
from quant.pipeline.state import PipelineState
from quant.pipeline.update_calendar import refresh_calendar
from quant.pipeline.update_market_eod import update_market_eod
from quant.pipeline.update_corporate import update_corporate_actions, update_corporate_filings
from quant.pipeline.update_macro import update_macro
from quant.pipeline.validate_data import validate_data
from quant.pipeline.build_adjusted import build_adjusted


def update_all(config, start, end, *, incremental=False):
    errors, results = {}, {}
    core = ('nse_bhavcopy', 'nse_security_master', 'nse_indices', 'nse_vix', 'security_history')
    state = PipelineState(config)
    try:
        if start.year < 2018:
            from datetime import date
            gate = audit_prices(config, date(2018, 1, 1), end)
            if gate['status'] != 'READY':
                raise ValueError('2018-present coverage must pass audit before extending to 2010')
        frame, report = refresh_calendar(config, start, end, incremental=incremental)
        state.record('nse_calendar', status=report['status'], day=end)
        results['calendar'] = report
    except Exception as error:
        errors['calendar'] = str(error)
        state.record('nse_calendar', status='FAILED', error=str(error))
    if 'calendar' not in errors:
        for name, update in [('market_eod', update_market_eod), ('corporate_actions', update_corporate_actions),
                             ('adjusted_prices', build_adjusted), ('corporate_filings', update_corporate_filings),
                             ('macro', update_macro)]:
            try:
                if incremental and name in ('market_eod', 'adjusted_prices'):
                    results[name] = update(config, start, end, incremental=True)
                else:
                    results[name] = update(config, start, end)
                if name == 'market_eod' and any(results[name].get(source, {}).get('status') != 'READY' for source in core):
                    errors[name] = 'Required market sources failed; inspect the market EOD report'
            except Exception as error:
                errors[name] = str(error)
                if name == 'adjusted_prices':
                    PipelineState(config).record(name, status='FAILED', error=str(error))
    report = validate_data(config, start, end, run_errors=errors, incremental=incremental)
    report['pipeline_stages'] = {name: 'FAILED' if name in errors else result.get('status', 'COMPLETED')
                                 for name, result in results.items() if isinstance(result, dict)}
    market = results.get('market_eod', {})
    if not errors and all(market.get(name, {}).get('status') == 'READY' for name in core):
        PipelineState(config).record('market_eod', status='READY', day=end, last_successful_session=str(end))
    else:
        PipelineState(config).record('market_eod', status='FAILED', error='Required EOD stages are incomplete')
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    args = parser.parse_args()
    report = update_all(args.config(config), args.start, args.end)
    print(json.dumps({'as_of': report['as_of'], 'status': report['status'], 'errors': report['errors']}, indent=2))
    return 0 if report['status'] == 'READY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
