from quant.backtest.validation import validation_levels


def test_statistical_and_economic_evidence_do_not_imply_production_validation():
    checks = dict.fromkeys(['positive_mean_IC','majority_positive_IC','monotonic_deciles',
        'adequate_OOS_length','mature_label_coverage','positive_OOS_excess','positive_net_performance',
        'survives_1_5x_costs','manageable_turnover','beats_simple_baselines','diversified_across_years',
        'verified_cost_schedule','diversified_across_clusters','OOS_IR_above_0_5','net_Sharpe_above_0_7'], True)
    levels = validation_levels(checks,acceptable_drawdown=True)
    assert levels['STATISTICAL_SIGNAL']['passed']
    assert levels['ECONOMICALLY_VIABLE']['passed']
    assert not levels['PRODUCTION_VALIDATED']['passed']
    assert validation_levels(checks,acceptable_drawdown=True,pit_data_verified=True,
        forward_test_completed=True,recommendation_history_tracked=True)['PRODUCTION_VALIDATED']['passed']


def test_missing_metrics_fail_all_levels():
    assert not any(row['passed'] for row in validation_levels({},acceptable_drawdown=False).values())
