"""Build dated research inputs without activating fundamental model switches."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

from quant.features.fundamentals import fundamental_observations, FUNDAMENTAL_FEATURE_VERSION
from quant.features.quality import quality_features, QUALITY_FIELDS
from quant.features.growth import growth_features, GROWTH_FIELDS
from quant.features.value import value_features, VALUE_FIELDS
from quant.features.bank_fundamentals import bank_features, BANK_QUALITY_FIELDS, BANK_GROWTH_FIELDS
from quant.features.share_history import share_history
from quant.storage.parquet_store import read_parquet_file, write_parquet
from quant.storage.research_store import write_json, digest_file, git_commit


def build_fundamental_features(price_keys, filings, anchors, events, coverage):
    keys = ['as_of','instrument_id']
    if price_keys.duplicated(keys).any():
        raise ValueError('Duplicate price feature keys')
    output = []
    for day, group in price_keys.groupby('as_of'):
        cutoff = pd.Timestamp(day).tz_localize('Asia/Kolkata')+pd.Timedelta(hours=15,minutes=30)
        observations = fundamental_observations(filings,cutoff)
        if observations.empty:
            continue
        shares = share_history(anchors,events,coverage,
            group[keys].assign(signal_timestamp=cutoff)).set_index('instrument_id')
        observations = observations[observations.instrument_id.isin(group.instrument_id)]
        prices = group.set_index('instrument_id').raw_close
        for row in observations.to_dict('records'):
            identity=row['instrument_id']
            row.update(quality_features(row), **growth_features(row), **bank_features(row))
            row.update(value_features(row,raw_price=prices.loc[identity],shares=shares.loc[identity].to_dict()))
            row['value_feature_valid']=bool(shares.loc[identity,'value_feature_valid'])
            output.append(row)
    columns = [*keys,'entity_type','fundamental_feature_version','value_feature_valid',
               *QUALITY_FIELDS,*GROWTH_FIELDS,*VALUE_FIELDS,*BANK_QUALITY_FIELDS,*BANK_GROWTH_FIELDS]
    frame = pd.DataFrame(output)
    for name in columns:
        if name not in frame:
            frame[name] = pd.Series(dtype='object' if name in (*keys,'entity_type','fundamental_feature_version') else 'float64')
    return frame


def main():
    from quant.pipeline.cli import parser_config
    parser,config=parser_config(__doc__)
    for name in ('price-keys','filings','anchors','capital-events','share-coverage'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    paths=[args.price_keys,args.filings,args.anchors,args.capital_events,args.share_coverage]
    if args.output.exists() or args.output.with_suffix('.manifest.json').exists():
        raise ValueError('Choose a new output path; research inputs are immutable')
    inputs=[read_parquet_file(p) for p in paths]
    # Filings must retain checksum-verified metadata and source documents.
    from quant.pipeline.audit_fundamental_coverage import verify_filing_archives
    inputs[1]=verify_filing_archives(inputs[1],args.config(config).data_dir)
    result=build_fundamental_features(*inputs)
    write_parquet(result,args.output)
    report=dict(status='RESEARCH_INPUTS_ONLY',feature_version=FUNDAMENTAL_FEATURE_VERSION,
        rows=len(result),input_sha256={str(p):digest_file(p) for p in paths},
        output_sha256=digest_file(args.output),factor_v2_enabled=False)
    from quant.research.specification import research_code_hashes
    report.update(git_commit=git_commit(),source_code_sha256=research_code_hashes())
    write_json(args.output.with_suffix('.manifest.json'),report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
