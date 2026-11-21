"""Offline seven-block V2 research candidate. Never activates a live model."""
import numpy as np
import pandas as pd

from quant.features.matrix import SCORE_FEATURES
from quant.features.normalize import normalize_cross_section
from quant.models.factor_v1 import score_factor_v1
from quant.features.quality import QUALITY_FIELDS
from quant.features.growth import GROWTH_FIELDS
from quant.features.value import VALUE_FIELDS
from quant.features.bank_fundamentals import BANK_QUALITY_FIELDS, BANK_GROWTH_FIELDS, BANK_VALUE_FIELDS

from quant.version import FACTOR_V2_VERSION
BLOCKS = ('momentum','relative_strength','quality','growth','value','low_risk','liquidity')


def same_universe_scores(price_features, fundamental_features, *, min_group_size=20):
    if min_group_size < 2:
        raise ValueError('Normalization requires at least two observations')
    keys = ['as_of','instrument_id']
    if fundamental_features.duplicated(keys).any():
        raise ValueError('Duplicate fundamental feature keys')
    full_v1 = score_factor_v1(price_features)
    joined = price_features.merge(fundamental_features, on=keys, validate='one_to_one', suffixes=('', '_fundamental'))
    joined['fundamental_valid'] = False
    for entity, fields in [('IND_AS_INDUSTRIAL', (*QUALITY_FIELDS,*GROWTH_FIELDS,*VALUE_FIELDS)),
                           ('IND_AS_BANK', (*BANK_QUALITY_FIELDS,*BANK_GROWTH_FIELDS,*BANK_VALUE_FIELDS))]:
        mask = joined.entity_type.eq(entity)
        if mask.any() and set(fields).issubset(joined.columns):
            joined.loc[mask,'fundamental_valid'] = np.isfinite(joined.loc[mask,list(fields)]).all(axis=1)
    joined['fundamental_valid'] &= joined.get('value_feature_valid', pd.Series(False, index=joined.index)).map(
        lambda value: isinstance(value, (bool, np.bool_)) and bool(value))
    joined = joined[joined.fundamental_valid & joined.eligible & joined.feature_valid].copy()
    for entity in ('IND_AS_INDUSTRIAL','IND_AS_BANK'):
        group_sizes = joined.loc[joined.entity_type.eq(entity)].groupby('as_of').instrument_id.transform('size')
        joined = joined.drop(index=group_sizes[group_sizes < min_group_size].index)
    # Recompute V1 normalization on exactly the covered population, rather than
    # preserving normalization influenced by names excluded by fundamentals.
    covered_prices = normalize_cross_section(joined[price_features.columns], SCORE_FEATURES)
    matched_v1 = score_factor_v1(covered_prices)
    candidate = matched_v1.merge(joined[[*keys,*[c for c in fundamental_features if c not in keys]]], on=keys, validate='one_to_one')
    for entity, blocks in [('IND_AS_INDUSTRIAL', (QUALITY_FIELDS,GROWTH_FIELDS,VALUE_FIELDS)),
                           ('IND_AS_BANK',(BANK_QUALITY_FIELDS,BANK_GROWTH_FIELDS,BANK_VALUE_FIELDS))]:
        for _, group in candidate[candidate.entity_type.eq(entity)].groupby('as_of'):
            for name, definitions in zip(('quality','growth','value'), blocks):
                scores = []
                for field, direction in definitions.items():
                    values = group[field].clip(group[field].quantile(.01),group[field].quantile(.99))
                    median = values.median()
                    mad = (values-median).abs().median()
                    z = ((values-median)/(1.4826*mad)).clip(-3,3) if mad > 0 else pd.Series(0.,index=values.index)
                    scores.append(direction*z)
                candidate.loc[group.index,name+'_score'] = sum(scores)/len(scores)
    candidate['raw_score'] = sum(candidate.get(b+'_score', pd.Series(index=candidate.index,dtype=float)) for b in BLOCKS)/len(BLOCKS)
    candidate['percentile_score'] = candidate.groupby('as_of').raw_score.rank(method='average',pct=True)*100
    candidate = candidate.sort_values([*keys[:1],'raw_score','instrument_id'],ascending=[True,False,True])
    candidate['rank'] = candidate.groupby('as_of').cumcount()+1
    candidate['model_name'], candidate['model_version'] = 'Factor V2 candidate', FACTOR_V2_VERSION
    return dict(full_v1=full_v1, matched_v1=matched_v1, factor_v2=candidate.reset_index(drop=True))
