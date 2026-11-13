import numpy as np

from quant.version import FEATURE_VERSION, MODEL_VERSION
from quant.features.matrix import SCORE_FEATURES


def score_factor_v1(features):
    if features.duplicated(['as_of', 'instrument_id']).any():
        raise ValueError('Duplicate feature keys')
    if not features.feature_version.eq(FEATURE_VERSION).all():
        raise ValueError('Unsupported feature version')
    result = features[features.eligible & features.feature_valid].copy()
    required = ['z_' + name for name in SCORE_FEATURES]
    if not np.isfinite(result[required]).all().all():
        raise ValueError('Missing normalized score inputs')
    z = lambda name: result['z_' + name]
    result['momentum_score'] = .20*z('mom_63') + .35*z('mom_126_ex_21') + .35*z('mom_252_ex_21') + .10*z('distance_52w_high')
    result['relative_strength_score'] = .5*z('rs_nifty500_63') + .5*z('rs_nifty500_126')
    result['low_risk_score'] = -(.35*z('vol_63') + .20*z('beta_252') + .25*z('abs_drawdown_252') + .20*z('cvar_95_252'))
    result['liquidity_score'] = .50*z('log_adv60') - .35*z('log_amihud60') + .15*z('trading_presence_252')
    result['raw_score'] = .40*result.momentum_score + .20*result.relative_strength_score + .20*result.low_risk_score + .20*result.liquidity_score
    result['percentile_score'] = result.groupby('as_of').raw_score.rank(method='average', pct=True) * 100
    result = result.sort_values(['as_of', 'raw_score', 'instrument_id'], ascending=[True, False, True])
    result['rank'] = result.groupby('as_of').cumcount() + 1
    result['universe_size'] = result.groupby('as_of').instrument_id.transform('size')
    result['model_name'] = 'Factor V1'
    result['model_version'] = MODEL_VERSION
    return result.reset_index(drop=True)
