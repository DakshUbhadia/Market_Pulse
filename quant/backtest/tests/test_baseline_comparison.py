from quant.backtest.report import baseline_comparison, BASELINE_METRICS
from quant.version import EVIDENCE_POLICY_VERSION


def test_risk_adjusted_table_preserves_metrics_and_reports_missing_evidence():
    strategy = dict(zip(BASELINE_METRICS,[.1,.8,1.,-.2,2.]))
    baselines = {'momentum':dict(zip(BASELINE_METRICS,[.15,.5,.7,-.4,3.])), 'unknown':{}}
    measured = {row['baseline']:row for row in baseline_comparison(strategy,baselines)}
    assert measured['momentum']['difference_information_ratio'] > 0
    assert measured['momentum']['difference_max_drawdown'] > 0
    assert measured['momentum']['difference_annualized_excess_return'] < 0
    assert measured['momentum']['assessed']
    assert measured['momentum']['evidence_policy_version'] == EVIDENCE_POLICY_VERSION
    assert not measured['unknown']['assessed']
    assert measured['unknown']['difference_Sharpe'] is None
