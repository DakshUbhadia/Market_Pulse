"""Archive official inventories and publish separately reviewed, dated circular evidence."""
import io
import json
import time

import pandas as pd

from quant.data.http import sha256
from quant.data.nse_lifecycle import SOURCE_PAGES, archive_source, inventory_links
from quant.data.lifecycle_normalize import normalize_events
from quant.storage.parquet_store import write_parquet
from quant.storage.research_store import write_json


def ingest_reviewed(config, records):
    normalized = []
    sources = {}
    for record in records:
        from quant.data.security_history import instrument_id
        canonical = instrument_id(record.get('isin'))
        if not canonical or record.get('instrument_id') != canonical:
            raise ValueError('Reviewed lifecycle identity must match the canonical ISIN identity')
        url = record['source_url']
        if url not in sources:
            sources[url] = archive_source(config,url)
            time.sleep(config.request_interval)
        content, provenance = sources[url]
        expected = record.get('source_sha256')
        if not expected or expected != sha256(content):
            raise ValueError('Reviewed evidence checksum must match the archived official document')
        normalized.append(dict(record, **provenance))
    frame = normalize_events(normalized)
    if frame.empty:
        raise ValueError('No reviewed lifecycle events supplied')
    path = config.data_dir/'normalized/lifecycle/events.parquet'
    if path.exists():
        previous = pd.read_parquet(path)
        duplicate = set(previous.lifecycle_event_id) & set(frame.lifecycle_event_id)
        if duplicate:
            raise ValueError('Lifecycle IDs are immutable; submit new evidence IDs for revisions')
        frame = pd.concat([previous,frame],ignore_index=True)
    write_parquet(frame,path)
    return frame


def refresh_inventories(config):
    reports = []
    for page in SOURCE_PAGES:
        try:
            content, metadata = archive_source(config,page)
            links = inventory_links(content,page)
            if not links:
                raise ValueError('No exchange inventory links found; source requires review')
            for link in links:
                time.sleep(config.request_interval)
                data, evidence = archive_source(config,link)
                frame = pd.read_csv(io.BytesIO(data)) if link.endswith('.csv') else pd.read_excel(io.BytesIO(data))
                # Inventory rows are discovery evidence, not PIT publication proof.
                frame = frame.astype('string')
                for key,value in evidence.items():
                    frame[key] = str(value)
                frame['verification_status'] = 'NEEDS_REVIEW'
                write_parquet(frame, config.data_dir/'normalized/lifecycle_inventory'/f'{evidence["source_sha256"]}.parquet')
                reports.append(dict(source_url=link,rows=len(frame),status='NEEDS_REVIEW'))
        except Exception as error:
            reports.append(dict(source_url=page,status='BLOCKED',reason=str(error)))
    return reports


def load_lifecycle(config):
    path = config.data_dir/'normalized/lifecycle/events.parquet'
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_parquet(path)
    for row in frame[frame.verification_status.eq('VERIFIED')].itertuples():
        raw = (config.data_dir/row.raw_path).resolve()
        if not raw.is_relative_to(config.data_dir.resolve()) or sha256(raw.read_bytes()) != row.source_sha256:
            raise ValueError('Lifecycle raw evidence is missing or its checksum has changed')
    return frame


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--events-json',type=str,help='Reviewed records with official document SHA-256')
    parser.add_argument('--refresh-lists',action='store_true')
    args = parser.parse_args()
    config = args.config(config)
    report = dict(status='BLOCKED',inventories=[],events=0)
    try:
        if args.refresh_lists:
            report['inventories'] = refresh_inventories(config)
        if args.events_json:
            from pathlib import Path
            report['events'] = len(ingest_reviewed(config,json.loads(Path(args.events_json).read_text())))
        report['status'] = 'EVIDENCE_ONLY' if report['events'] else 'NEEDS_REVIEW'
    except (ValueError,OSError,KeyError) as error:
        report['reason'] = str(error)
    write_json(config.data_dir/'reports/lifecycle-coverage.json',report)
    print(json.dumps(report,indent=2))
    return 0 if report['status'] == 'EVIDENCE_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
