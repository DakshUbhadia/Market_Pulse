import pandas as pd
import pytest

from quant.features.matrix import SCORE_FEATURES
from quant.models.factor_v1 import score_factor_v1
from quant.version import FEATURE_VERSION


def test_factor_weights_percentiles_and_ineligible_exclusion():
    frame = pd.DataFrame(dict(as_of=[pd.Timestamp('2024-01-01')]*3, instrument_id=['a','b','c'],
                              symbol=['A','B','C'], eligible=[True, True, False], feature_valid=True,
                              feature_version=FEATURE_VERSION))
    for name in SCORE_FEATURES:
        frame['z_'+name] = 0.
    frame.loc[0, 'z_mom_63'] = 1
    frame.loc[2, 'z_mom_63'] = 1000
    result = score_factor_v1(frame)
    assert result.instrument_id.tolist() == ['a', 'b']
    assert result.raw_score.iloc[0] == pytest.approx(.4*.2)
    assert result.percentile_score.tolist() == [100, 50]
    assert result.universe_size.tolist() == [2, 2]
