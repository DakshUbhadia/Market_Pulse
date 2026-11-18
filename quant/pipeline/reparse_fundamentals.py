"""Bounded offline parser replay over checksum-verified archived documents."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json

import pandas as pd

from quant.data.taxonomy_registry import filing_family, TAXONOMY_VERSION
from quant.data.xbrl import extract_financials
from quant.storage.parquet_store import read_parquet_file, write_parquet
from quant.storage.research_store import digest_file, git_commit, write_json


def reparse_fundamentals(config, source_data_dir, start, end, *, limit=100, offset=0):
    if not 1 <= limit <= 250 or offset < 0 or start > end:
        raise ValueError('Replay requires 1-250 documents, a nonnegative offset and a valid date range')
    source = Path(source_data_dir).resolve()
    paths = sorted((source/'normalized/financials').rglob('*.parquet'))
    frames = [read_parquet_file(p) for p in paths]
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if frame.empty or 'document_raw_path' not in frame:
        raise ValueError('No archived financial documents')
    times = pd.to_datetime(frame.exchange_disseminated_at, utc=True, errors='coerce')
    frame = frame[times.ge(pd.Timestamp(start, tz='Asia/Kolkata'))
                  & times.lt(pd.Timestamp(end, tz='Asia/Kolkata')+pd.Timedelta(days=1))
                  & frame.document_raw_path.notna()]
    frame = frame.sort_values(['filing_id']).drop_duplicates('filing_id').iloc[offset:offset+limit].copy()
    original = frame.copy()
    rows, review = [], []
    for i, row in original.iterrows():
        record = row.to_dict()
        try:
            # Verify both archives independently of the original parser status.
            for path_key, hash_key in [('metadata_raw_path','source_sha256'), ('document_raw_path','document_sha256')]:
                path = Path(row[path_key])
                path = path if path.is_absolute() else source/path
                if not path.resolve().is_relative_to(source) or not path.is_file() or digest_file(path) != row[hash_key]:
                    raise ValueError('Missing or changed archived bytes: '+path_key)
            if row.standalone_or_consolidated not in ('Consolidated','Standalone','Non-Consolidated'):
                raise ValueError('Unknown consolidation basis')
            family = filing_family(row)
            path = Path(row.document_raw_path)
            path = path if path.is_absolute() else source/path
            record.update(extract_financials(path.read_bytes(), row.period_end,
                period_start=row.period_start if pd.notna(row.period_start) else None,
                consolidated=row.standalone_or_consolidated == 'Consolidated', entity_type=family,
                bank=family == 'IND_AS_BANK'))
            if record['parser_status'] != 'PARSED':
                raise ValueError('Unsupported or ambiguous facts')
        except (ValueError, OSError, KeyError) as error:
            record['parser_status'] = 'NEEDS_REVIEW'
            review.append(dict(filing_id=row.filing_id, reason=str(error)))
        rows.append(record)
    result = pd.DataFrame(rows)
    stamp = datetime.now(timezone.utc)
    folder = config.data_dir/'research/fundamental-replays'/f'{stamp:%Y%m%dT%H%M%S%f}-{uuid4().hex[:8]}'
    write_parquet(result, folder/'filings.parquet')
    report = dict(status='REPLAY_COMPLETE' if rows else 'EMPTY_BATCH', git_commit=git_commit(),
        source_data_dir=str(source), start=str(start), end=str(end), limit=limit, offset=offset,
        next_offset=offset+len(rows), documents_attempted=len(rows),
        parsed=sum(r['parser_status']=='PARSED' for r in rows), review=review,
        taxonomy_version=TAXONOMY_VERSION, parser_version='financial_xbrl_2.0.0',
        input_metadata_sha256={str(p.relative_to(source)):digest_file(p) for p in paths},
        document_sha256=sorted(set(original.document_sha256)) if len(original) else [],
        output_sha256=digest_file(folder/'filings.parquet'), report_path=str(folder/'report.json'),
        source_corpus_modified=False, certifies_coverage=False, factor_v2_enabled=False)
    from quant.research.specification import research_code_hashes
    report['source_code_sha256']=research_code_hashes()
    write_json(folder/'report.json', report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--source-data-dir', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--offset', type=int, default=0)
    args = parser.parse_args()
    report = reparse_fundamentals(args.config(config), args.source_data_dir, args.start, args.end,
                                 limit=args.limit, offset=args.offset)
    print(json.dumps({k:v for k,v in report.items() if k not in ('input_metadata_sha256','document_sha256','source_code_sha256')}, indent=2))
    return 0 if report['documents_attempted'] and not report['review'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
