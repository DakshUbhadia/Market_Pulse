"""Replay frozen monthly decisions with the historical engine, then seal each day."""
from quant.identity.transitions import TRANSITION_VERSION
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from quant.backtest.engine import run_backtest, monthly_signal_dates
from quant.forward.signal_store import append_record, read_signals, content_hash
from quant.storage.research_store import clean_json
from quant.version import (MODEL_VERSION, FEATURE_VERSION, PORTFOLIO_ACCOUNTING_VERSION,
                           LIFECYCLE_POLICY_VERSION)


def update_shadow(root, prices, sessions, *, as_of, portfolio, cost_model, corporate_actions,
                  lifecycle_events, lifecycle_scenario, security_transitions=None, transition_data_dir=None, model_card=None):
    batches, scores = read_signals(root)
    if scores.empty:
        raise ValueError('No frozen forward signals')
    selected = scores[scores.as_of <= pd.Timestamp(as_of)]
    expected = dict(model_version=MODEL_VERSION, feature_version=FEATURE_VERSION,
        security_transition_version=TRANSITION_VERSION,portfolio_accounting_version=PORTFOLIO_ACCOUNTING_VERSION, lifecycle_policy_version=LIFECYCLE_POLICY_VERSION)
    if model_card is not None:
        from quant.models.model_card import verify_model_card
        verify_model_card(model_card)
        expected.update(model_version=model_card['model_version'], feature_version=model_card['feature_version'])
        if any(b['settings'].get('model_card_sha256') != model_card['sha256'] for b in batches):
            raise ValueError('Shadow cohort differs from registered model card')
    if selected.empty or any(not selected[key].eq(value).all() for key,value in expected.items()):
        raise ValueError('Forward policy changed; create a separate paper cohort')
    settings = [batch['settings'] for batch in batches if batch['as_of'] <= str(as_of)[:10]]
    if any(setting != settings[0] for setting in settings):
        raise ValueError('Shadow portfolio settings changed within a cohort')
    if (settings[0]['portfolio'] != clean_json(asdict(portfolio))
            or settings[0]['costs'] != clean_json(asdict(cost_model))
            or settings[0]['lifecycle_scenario'] != lifecycle_scenario):
        raise ValueError('Shadow runtime differs from the frozen portfolio policy')
    result = run_backtest(prices, selected, sessions, start=selected.as_of.min(), end=as_of,
        portfolio=portfolio, cost_model=cost_model, corporate_actions=corporate_actions,
        lifecycle_events=lifecycle_events, lifecycle_scenario=lifecycle_scenario, security_transitions=security_transitions, transition_data_dir=transition_data_dir,
        signal_dates=[day for day in monthly_signal_dates(sessions) if day >= selected.as_of.min()])
    # Corrections must be investigated; never silently replace a previous NAV.
    curve = result.equity_curve.set_index('trade_date')
    for path in sorted((Path(root)/'shadow').glob('*.json')):
        old = json.loads(path.read_text(encoding='utf-8'))
        if content_hash({k:v for k,v in old.items() if k != 'sha256'}) != old['sha256']:
            raise ValueError('Frozen shadow record checksum changed')
        day = pd.Timestamp(old['as_of'])
        if day <= pd.Timestamp(as_of) and (day not in curve.index or not np.isclose(
                old['equity']['nav'], curve.loc[day,'nav'], rtol=1e-10, atol=1e-6)):
            raise ValueError('Previously frozen shadow NAV changed; investigate corrected inputs')
    day = pd.Timestamp(as_of)
    if day not in curve.index:
        raise ValueError('Shadow date is not an exchange session')
    record = dict(as_of=str(day.date()), signal_batches=[b['sha256'] for b in batches if b['as_of'] <= str(day.date())],
        settings=settings[0], equity=curve.loc[day].to_dict(),
        trades=result.trades[result.trades.trade_date.eq(day)].to_dict('records') if not result.trades.empty else [],
        holdings=result.holdings[result.holdings.trade_date.eq(day)].to_dict('records') if not result.holdings.empty else [],
        lifecycle=result.lifecycle[result.lifecycle.trade_date.eq(day)].to_dict('records') if not result.lifecycle.empty else [],
        dividends=result.dividends[result.dividends.trade_date.eq(day)].to_dict('records') if not result.dividends.empty else [],
        validation_level='FORWARD_PAPER_ONLY')
    record['sha256'] = content_hash(record)
    return append_record(Path(root)/'shadow'/f'{day.date()}.json', record)
