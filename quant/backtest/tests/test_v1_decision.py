from quant.backtest.report import v1_research_decision


def test_next_research_gate_is_separate_from_production_and_has_no_cluster_cap():
    names = ('positive_mean_IC','positive_median_IC','majority_positive_IC','monotonic_deciles',
        'positive_OOS_excess','positive_net_performance','reasonable_drawdown','manageable_turnover',
        'survives_1_5x_costs','diversified_across_years','mature_label_coverage','adequate_OOS_length')
    evidence = dict(checks=dict.fromkeys(names,True),cluster_check='ASSESSED',highest_validation_level='STATISTICAL_SIGNAL')
    evidence['checks']['verified_cost_schedule'] = False
    evidence['checks']['diversified_across_clusters'] = False
    metrics = dict(annualized_excess_return=.05)
    baselines = dict(momentum_12_1_top25=dict(annualized_excess_return=.04))
    decision = v1_research_decision(evidence,metrics,baselines)
    assert decision['decision'] == 'GO_FURTHER_V1_RESEARCH' and not decision['ML_authorized']
    assert decision['research_outcome'] == 'PASS_RESEARCH'
    baselines['momentum_12_1_top25']['annualized_excess_return'] = .06
    assert v1_research_decision(evidence,metrics,baselines)['decision'] == 'NO_GO_INVESTIGATE'
    assert v1_research_decision(evidence,metrics,baselines)['research_outcome'] == 'NO_GO'
    evidence['checks']['adequate_OOS_length'] = False
    assert v1_research_decision(evidence,metrics,baselines)['research_outcome'] == 'INCONCLUSIVE'
