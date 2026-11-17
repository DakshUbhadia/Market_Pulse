"""Diagnostic research levels; every production prerequisite is explicit."""


def validation_levels(checks, *, acceptable_drawdown, pit_data_verified=False,
                      forward_test_completed=False, recommendation_history_tracked=False):
    statistical_names = ('positive_mean_IC','positive_median_IC','majority_positive_IC','monotonic_deciles',
                         'adequate_OOS_length','mature_label_coverage')
    economic_names = ('positive_OOS_excess','positive_net_performance','survives_1_5x_costs',
                      'manageable_turnover','beats_simple_baselines','diversified_across_years')
    statistical = {name:bool(checks.get(name,False)) for name in statistical_names}
    economic = dict(statistical_signal=all(statistical.values()), acceptable_drawdown=bool(acceptable_drawdown),
                    **{name:bool(checks.get(name,False)) for name in economic_names})
    production = dict(economically_viable=all(economic.values()),
        verified_historical_costs=bool(checks.get('verified_cost_schedule',False)),
        PIT_diversification=bool(checks.get('diversified_across_clusters',False)),
        PIT_data_requirements=bool(pit_data_verified), forward_paper_test_completed=bool(forward_test_completed),
        immutable_recommendation_history=bool(recommendation_history_tracked),
        OOS_IR_above_0_5=bool(checks.get('OOS_IR_above_0_5',False)),
        net_Sharpe_above_0_7=bool(checks.get('net_Sharpe_above_0_7',False)))
    return {name:dict(passed=all(values.values()),checks=values) for name,values in
            [('STATISTICAL_SIGNAL',statistical),('ECONOMICALLY_VIABLE',economic),('PRODUCTION_VALIDATED',production)]}
