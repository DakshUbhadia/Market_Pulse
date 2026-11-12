"""Single scheduled refresh. Always write data health, including after failures."""
import json

from quant.pipeline.audit_prices import audit_prices
from quant.pipeline.state import PipelineState
from quant.pipeline.update_calendar import refresh_calendar
from quant.pipeline.update_market_eod import update_market_eod
from quant.pipeline.update_corporate import update_corporate
from quant.pipeline.update_macro import update_macro
from quant.pipeline.validate_data import validate_data
from quant.pipeline.build_adjusted import build_adjusted


def update_all(config, start, end):
    errors, results = {}, {}
    state = PipelineState(config)
    try:
        if start.year < 2018:
            from datetime import date
            gate = audit_prices(config, date(2018, 1, 1), end)
            if gate['status'] != 'READY':
                raise ValueError('2018-present coverage must pass audit before extending to 2010')
        frame, report = refresh_calendar(config, start, end)
        state.record('nse_calendar', status=report['status'], day=end)
        results['calendar'] = report
    except Exception as error:
        errors['calendar'] = str(error)
        state.record('nse_calendar', status='FAILED', error=str(error))
    if 'calendar' not in errors:
        for name, update in [('market_eod', update_market_eod), ('corporate', update_corporate),
                             ('macro', update_macro), ('adjusted_prices', build_adjusted)]:
            try:
                results[name] = update(config, start, end)
            except Exception as error:
                errors[name] = str(error)
                if name == 'adjusted_prices':
                    PipelineState(config).record(name, status='FAILED', error=str(error))
    report = validate_data(config, start, end, run_errors=errors)
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
