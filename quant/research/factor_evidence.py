"""Factor evidence and explicit missingness from computed PIT inputs."""
import numpy as np
import pandas as pd
from quant.backtest.metrics import diagnostics
from quant.models.factor_v2 import BLOCKS
from quant.features.quality import QUALITY_FIELDS
from quant.features.growth import GROWTH_FIELDS
from quant.features.value import VALUE_FIELDS
from quant.features.bank_fundamentals import BANK_QUALITY_FIELDS, BANK_GROWTH_FIELDS, BANK_VALUE_FIELDS


def factor_evidence(scores, labels, window):
    cross = scores[pd.to_datetime(scores.as_of).between(pd.Timestamp(window['from']), pd.Timestamp(window['to']))]
    rows, correlations = [], []
    for block in BLOCKS:
        ranked = cross.copy()
        ranked['raw_score'] = ranked[block+'_score']
        ic, deciles, summary = diagnostics(ranked, labels)
        spread = deciles.groupby('decile').excess_return.mean() if len(deciles) else pd.Series(dtype=float)
        rows.append(dict(block=block, **summary,
            decile_spread=float(spread.loc[10]-spread.loc[1]) if {1, 10} <= set(spread.index) else None,
            factor_coverage=float(np.isfinite(ranked.raw_score).mean()) if len(ranked) else None))
    for day, group in cross.groupby('as_of'):
        matrix = group[[b+'_score' for b in BLOCKS]].corr(method='spearman')
        for i, a in enumerate(BLOCKS):
            for b in BLOCKS[i+1:]:
                correlations.append(dict(as_of=day, block_a=a, block_b=b, correlation=matrix.loc[a+'_score', b+'_score']))
    return rows, pd.DataFrame(correlations)


def missingness_attribution(features, fundamentals):
    keys = ['as_of', 'instrument_id']
    joined = features.merge(fundamentals, on=keys, how='left', suffixes=('', '_fundamental'), validate='one_to_one', indicator=True)
    rows = []
    for row in joined.to_dict('records'):
        for block in BLOCKS:
            reason = None
            entity = row.get('entity_type')
            if block in ('quality', 'growth', 'value'):
                if row['_merge'] == 'left_only':
                    reason = 'NO_FILING'
                elif entity not in ('IND_AS_INDUSTRIAL', 'IND_AS_BANK'):
                    reason = 'UNSUPPORTED_ENTITY'
                elif block == 'value' and row.get('value_feature_valid') is not True:
                    reason = 'NO_VERIFIED_SHARES'
                elif (block in ('quality', 'value') and not row.get('annual_fresh', False)
                      or block == 'growth' and not row.get('quarter_fresh', False)):
                    reason = 'STALE_FILING'
                else:
                    fields = ({'quality': BANK_QUALITY_FIELDS, 'growth': BANK_GROWTH_FIELDS, 'value': BANK_VALUE_FIELDS}
                              if entity == 'IND_AS_BANK' else
                              {'quality': QUALITY_FIELDS, 'growth': GROWTH_FIELDS, 'value': VALUE_FIELDS})[block]
                    if not all(pd.notna(row.get(f)) and np.isfinite(row[f]) for f in fields):
                        reason = 'BANK_SCHEMA_MISMATCH' if entity == 'IND_AS_BANK' else 'INSUFFICIENT_HISTORY'
            elif not row.get('feature_valid', False):
                reason = 'INSUFFICIENT_HISTORY'
            rows.append(dict(**{k: row[k] for k in keys}, block=block, missing=reason is not None, reason=reason))
    return pd.DataFrame(rows)
