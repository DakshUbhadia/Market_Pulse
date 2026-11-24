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
from quant.research.coverage_policy import reliable_interval

MATRIX_INPUT_ROLES = ('price_features', 'fundamental_features', 'filings', 'anchors', 'capital_events', 'share_coverage')


def prepare_v2_matrix(price_features, fundamental_features, *, min_group_size=20, coverage_inputs=None):
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
    if coverage_inputs is not None:
        from quant.features.fundamental_snapshot import fundamental_snapshot
        from quant.features.share_history import share_history
        from quant.research.factor_evidence import missingness_attribution

        filings, anchors, events, intervals = coverage_inputs
        missingness = missingness_attribution(price_features[price_features.eligible.eq(True)], fundamental_features)
    rows = []
    for day, cross in price_features[price_features.eligible.eq(True)].groupby('as_of'):
        liquid = cross.dropna(subset=['adv60']).sort_values(['adv60', 'instrument_id'], ascending=[False, True]).head(100)
        count = sum((day, iid) in covered for iid in cross.instrument_id)
        top = sum((day, iid) in covered for iid in liquid.instrument_id)
        def value_valid(iid):
            if (day, iid) not in fundamentals.index:
                return False
            value = fundamentals.loc[(day, iid)].get('value_feature_valid')
            return isinstance(value, (bool, np.bool_)) and bool(value)
        value_missing = sum(not value_valid(iid) for iid in cross.instrument_id)
        row = dict(as_of=str(pd.Timestamp(day).date()), eligible=len(cross), top100_count=len(liquid),
            complete_seven_block_rows=count, verified_value_missing=int(value_missing),
            overall_coverage=100*count/len(cross) if len(cross) else None,
            top100_coverage=100*top/len(liquid) if len(liquid) else None)
        if coverage_inputs is not None:
            cutoff = day.tz_localize('Asia/Kolkata')+pd.Timedelta(hours=15, minutes=30)
            observations = fundamental_snapshot(filings, cutoff, instrument_ids=set(cross.instrument_id))
            chains = share_history(anchors, events, intervals, cross[keys].assign(signal_timestamp=cutoff))
            filing_names = set(observations.instrument_id) if len(observations) else set()
            share_names = set(chains.loc[chains.value_feature_valid.eq(True), 'instrument_id'])
            block_names = {iid for iid in cross.instrument_id if (day, iid) in covered}
            joint = filing_names & share_names & block_names
            liquid_names = set(liquid.instrument_id)

            def counts(names):
                return dict(eligible=len(names), usable_filings=len(names & filing_names),
                    verified_shares=len(names & share_names), filings_and_shares=len(names & filing_names & share_names),
                    complete_blocks=len(names & block_names), joint=len(names & joint))

            entity = (cross.set_index('instrument_id')['entity_type'] if 'entity_type' in cross
                      else fundamentals.loc[fundamentals.index.get_level_values('as_of') == day, 'entity_type'].droplevel('as_of'))
            members = cross.instrument_id.map(entity).fillna('UNKNOWN')
            losses = missingness[missingness.as_of.eq(day) & missingness.missing
                                 & missingness.instrument_id.isin(filing_names & share_names)]
            reasons = {block: group.reason.value_counts().to_dict() for block, group in losses.groupby('block')}
            row.update(overall=counts(set(cross.instrument_id)), top100=counts(liquid_names),
                eligible_ids_sha256=content_hash(sorted(cross.instrument_id)),
                top100_ids_sha256=content_hash(sorted(liquid_names)),
                entities={str(kind): counts(set(cross.loc[members.eq(kind), 'instrument_id']))
                          for kind in sorted(members.unique())},
                joint_overall_pct=100*len(joint)/len(cross),
                joint_top100_pct=100*len(joint & liquid_names)/len(liquid) if len(liquid) else None,
                missing_blocks_after_filing_and_shares=reasons,
                normalization_exclusions=len((filing_names & share_names) - block_names - set(losses.instrument_id)))
        rows.append(row)
    complete = bool(rows) and all(r['top100_coverage'] is not None
        and r['overall_coverage'] >= 80 and r['top100_coverage'] >= 90 for r in rows)
    report = dict(status='COMPLETE_RESEARCH_INPUTS' if complete else 'INCOMPLETE',
        required_blocks=list(BLOCKS), periods=rows, value_required=True, full_v2_enabled=False,
        specification_status='DRAFT', frozen=False, historical_validation=False, promotion_eligible=False,
        authority='DATA_PREPARATION_ONLY', covered_keys_sha256=content_hash(sorted((str(d), i) for d, i in covered)))
    if coverage_inputs is not None:
        joint_rows = [dict(as_of=r['as_of'], thresholds_met=bool(r['joint_top100_pct'] is not None
                      and r['joint_overall_pct'] >= 80 and r['joint_top100_pct'] >= 90)) for r in rows]
        start = reliable_interval(joint_rows)
        report.update(joint_policy='PIT_FILING_SHARE_SEVEN_BLOCK_AUDIT_1.0.0',
            joint_status='THRESHOLDS_MET' if start else 'BLOCKED',
            joint_start=start, joint_end=rows[-1]['as_of'] if start else None)
    return arms, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--price-features', type=Path, required=True)
    parser.add_argument('--fundamental-features', type=Path, required=True)
    parser.add_argument('--archive-root', type=Path, help='Root used to verify original filing and share evidence bytes')
    for name in ('filings', 'anchors', 'capital-events', 'share-coverage'):
        parser.add_argument('--'+name, type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a new matrix preparation directory')
    inputs = [args.price_features.resolve(), args.fundamental_features.resolve()]
    coverage_inputs = None
    evidence = [args.archive_root, args.filings, args.anchors, args.capital_events, args.share_coverage]
    if any(evidence):
        if not all(evidence):
            parser.error('Joint coverage needs --archive-root, --filings, --anchors, --capital-events and --share-coverage')
        from quant.pipeline.audit_fundamental_coverage import verify_filing_archives
        from quant.pipeline.audit_share_history_coverage import verify_share_archives
        inputs.extend(p.resolve() for p in evidence[1:])
        coverage_inputs = [verify_filing_archives(read_parquet_file(args.filings), args.archive_root),
            *(verify_share_archives(read_parquet_file(p), args.archive_root) for p in evidence[2:])]
    hashes = {str(p): digest_file(p) for p in inputs}
    arms, report = prepare_v2_matrix(*(read_parquet_file(p) for p in inputs[:2]), coverage_inputs=coverage_inputs)
    if hashes != {str(p): digest_file(p) for p in inputs}:
        raise ValueError('Matrix inputs changed during preparation')
    for name, frame in arms.items():
        write_parquet(frame, args.output/(name+'.parquet'))
    report['input_sha256'] = hashes
    if coverage_inputs is not None:
        report['input_roles'] = dict(zip(MATRIX_INPUT_ROLES, map(str, inputs), strict=True))
    write_json(args.output/'matrix-status.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
