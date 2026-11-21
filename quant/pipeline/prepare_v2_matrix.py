"""Inspect all seven V2 blocks without freezing a policy or issuing a decision."""
import json
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from quant.models.factor_v2 import same_universe_scores, BLOCKS
from quant.forward.signal_store import content_hash
from quant.storage.parquet_store import read_parquet_file, write_parquet
from quant.storage.research_store import write_json, digest_file


def prepare_v2_matrix(price_features, fundamental_features, *, min_group_size=20):
    if min_group_size < 20:
        raise ValueError('Full V2 preparation retains at least 20 names per normalization group')
    price_features, fundamental_features = price_features.copy(), fundamental_features.copy()
    for frame in (price_features, fundamental_features):
        frame['as_of'] = pd.to_datetime(frame.as_of, format='mixed')
    arms = same_universe_scores(price_features, fundamental_features, min_group_size=min_group_size)
    candidate = arms['factor_v2']
    keys = ['as_of', 'instrument_id']
    covered = set(map(tuple, candidate[keys].to_numpy()))
    fundamentals = fundamental_features.set_index(keys)
    rows = []
    for day, cross in price_features[price_features.eligible.eq(True)].groupby('as_of'):
        liquid = cross.sort_values(['adv60', 'instrument_id'], ascending=[False, True]).head(100)
        count = sum((day, iid) in covered for iid in cross.instrument_id)
        top = sum((day, iid) in covered for iid in liquid.instrument_id)
        def value_valid(iid):
            if (day, iid) not in fundamentals.index:
                return False
            value = fundamentals.loc[(day, iid)].get('value_feature_valid')
            return isinstance(value, (bool, np.bool_)) and bool(value)
        value_missing = sum(not value_valid(iid) for iid in cross.instrument_id)
        rows.append(dict(as_of=str(pd.Timestamp(day).date()), eligible=len(cross), top100_count=len(liquid),
            complete_seven_block_rows=count, verified_value_missing=int(value_missing),
            overall_coverage=100*count/len(cross) if len(cross) else None,
            top100_coverage=100*top/len(liquid) if len(liquid) else None))
    complete = bool(rows) and all(r['overall_coverage'] >= 80 and r['top100_coverage'] >= 90 for r in rows)
    report = dict(status='COMPLETE_RESEARCH_INPUTS' if complete else 'INCOMPLETE',
        required_blocks=list(BLOCKS), periods=rows, value_required=True, full_v2_enabled=False,
        specification_status='DRAFT', frozen=False, historical_validation=False, promotion_eligible=False,
        authority='DATA_PREPARATION_ONLY', covered_keys_sha256=content_hash(sorted((str(d), i) for d, i in covered)))
    return arms, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--price-features', type=Path, required=True)
    parser.add_argument('--fundamental-features', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new matrix preparation directory')
    inputs = [args.price_features, args.fundamental_features]
    arms, report = prepare_v2_matrix(*(read_parquet_file(p) for p in inputs))
    for name, frame in arms.items():
        write_parquet(frame, args.output/(name+'.parquet'))
    report['input_sha256'] = {str(p): digest_file(p) for p in inputs}
    write_json(args.output/'matrix-status.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
