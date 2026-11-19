"""One bounded official discovery/acquisition batch followed by full replanning."""
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from quant.data.fundamental_discovery_gap import build_discovery_gap, select_discovery_batch
from quant.data.nse_client import NseClient, NseSourceError
from quant.data.nse_financials import PATH, parse_financial_filings
from quant.data.official_filing_sources import OfficialDocumentClient, validate_official_source
from quant.data.normalization import record_id
from quant.forward.signal_store import content_hash
from quant.pipeline.audit_fundamental_coverage import audit_fundamental_coverage, verify_filing_archives
from quant.pipeline.plan_fundamental_acquisition import plan_acquisition
from quant.pipeline.report_fundamental_coverage_ceiling import coverage_ceiling
from quant.pipeline.update_corporate import archive_filings, windows
from quant.storage.parquet_store import read_parquet_file, write_parquet
from quant.storage.research_store import digest_file, write_json


def discover_targeted(config, universe, coverage, ceiling, filings, sessions, history, *,
                      attempts=None, max_instruments=25, max_cells=100, max_requests=25,
                      max_documents=25, client_factory=NseClient, fallback_manifest=(), issuer_hosts=(),
                      completed_queries=()):
    if not 1 <= max_requests <= 100 or not 1 <= max_documents <= 100:
        raise ValueError('Bound requests and document acquisition to 1-100 each')
    attempts = attempts or {}
    # Check the candidate corpus too: a ledger from a changed corpus is stale.
    expected = coverage_ceiling(universe, coverage, filings, attempts=attempts)
    if content_hash(expected['periods']) != content_hash(ceiling['periods']):
        raise ValueError('Discovery ceiling is stale relative to filings and attempts')
    ledger = build_discovery_gap(universe, coverage, ceiling, filings)
    targets = select_discovery_batch(ledger, max_instruments=max_instruments, max_cells=max_cells)
    root = config.data_dir/'research/discovery-batches'/uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    write_json(root/'input-ledger.json', ledger)
    write_json(root/'selected-cells.json', targets)
    names = {r['instrument_id'] for r in targets}
    discovered, responses, errors, review = [], [], [], []
    count, acquired, skipped, seen_documents = 0, 0, 0, set()
    completed = {r['query_sha256']: r for r in completed_queries}
    existing_ids = set(filings.filing_id) | set(filings.get('metadata_filing_id', pd.Series(dtype=str)).dropna()) if len(filings) else set()
    for previous in completed.values():
        path = Path(previous['raw_path']).resolve()
        if (not path.is_relative_to(config.data_dir.resolve()) or not path.is_file()
                or digest_file(path) != previous['sha256']
                or not set(previous.get('metadata_filing_ids', [])).issubset(existing_ids)):
            raise ValueError('Previous discovery evidence changed or is absent from the supplied filing corpus')
    if targets:
        with client_factory(config) as client:
            stopped = False
            # Group in priority order. Requests use explicit bounded disclosure
            # windows; the symbol is never projected into a current universe.
            for iid in dict.fromkeys(r['instrument_id'] for r in targets):
                cells = [r for r in targets if r['instrument_id'] == iid]
                begin = min(pd.Timestamp(r['annual_period_end_no_earlier_than']) for r in cells).date()
                end = max(pd.Timestamp(r['as_of']) for r in cells).date()
                symbol = cells[0]['symbol']
                if not isinstance(symbol, str) or not symbol:
                    errors.append(dict(instrument_id=iid, reason='MISSING_DATED_SYMBOL'))
                    continue
                for start, stop in windows(begin, end, days=90):
                    for period in ('Annual', 'Quarterly'):
                        params = dict(index='equities', symbol=symbol,
                            from_date=start.strftime('%d-%m-%Y'), to_date=stop.strftime('%d-%m-%Y'), period=period)
                        query_hash = content_hash(dict(path=PATH, params=params, instrument_id=iid))
                        if query_hash in completed:
                            responses.append(completed[query_hash])
                            skipped += 1
                            continue
                        if count >= max_requests:
                            stopped = True
                            break
                        count += 1
                        try:
                            payload = client.get_json(PATH, params=params, dataset='targeted_financial_discovery')
                            raw = client.last_response
                            frame = parse_financial_filings(payload, raw)
                            responses.append(dict(instrument_id=iid, symbol=symbol, raw_path=str(raw.path),
                                sha256=raw.sha256, source_url=raw.source_url, retrieved_at=raw.fetched_at,
                                source_type='NSE_OFFICIAL', source_exchange='NSE',
                                reason_primary_source_unavailable=None, query_sha256=query_hash,
                                metadata_filing_ids=list(frame.loc[frame.symbol.eq(symbol), 'filing_id']) if len(frame) else []))
                            if len(frame):
                                frame = frame[frame.symbol.eq(symbol)].copy()
                                frame['source_type'], frame['source_exchange'] = 'NSE_OFFICIAL', 'NSE'
                                frame['retrieved_at'] = raw.fetched_at
                                frame['reason_primary_source_unavailable'] = None
                                frame['parser_status'] = 'NOT_ATTEMPTED'
                                frame['_document_attempted'] = False
                                # Metadata is persisted before any document attempt.
                                write_parquet(frame, root/f'metadata-{count:03d}.parquet')
                                for index, row in frame.iterrows():
                                    url = row.get('source_document')
                                    if acquired >= max_documents or not isinstance(url, str) or url in seen_documents:
                                        continue
                                    validate_official_source(dict(source_type='NSE_OFFICIAL', source_exchange='NSE', source_url=url))
                                    seen_documents.add(url)
                                    acquired += 1
                                    parsed, findings = archive_filings(client, frame.loc[[index]], 'financials', history)
                                    parsed['_document_attempted'] = True
                                    if client.last_response:
                                        parsed['retrieved_at'] = client.last_response.fetched_at
                                    frame = frame.drop(index)
                                    frame = pd.concat([frame, parsed])
                                    review.extend(findings)
                                discovered.append(frame)
                        except (ValueError, OSError, NseSourceError) as error:
                            raw = client.last_response
                            errors.append(dict(instrument_id=iid, symbol=symbol, reason=str(error),
                                http_status=getattr(error, 'http_status', None),
                                raw_path=str(raw.path) if raw else None, sha256=raw.sha256 if raw else None))
                            # One source outage ends this route for the batch.
                            stopped = True
                            break
                    if stopped:
                        break
                if stopped:
                    break
    # BSE/issuer documents require explicit reviewed metadata, including an
    # exchange dissemination timestamp. Retrieval time never substitutes for it.
    for source in sorted(fallback_manifest, key=lambda r: 0 if r.get('source_type') == 'BSE_OFFICIAL' else 1):
        if acquired >= max_documents:
            break
        if source.get('instrument_id') not in names:
            continue
        validate_official_source(source, issuer_hosts=issuer_hosts)
        cutoff = pd.Timestamp(source['exchange_disseminated_at'])
        if cutoff.tzinfo is None:
            raise ValueError('Fallback metadata requires verified historical exchange dissemination')
        # The reviewed manifest is archived as metadata; a filename date or
        # issuer upload date alone is not accepted as exchange-time evidence.
        proof_path = (config.data_dir/source['dissemination_evidence_path']).resolve()
        if (not proof_path.is_relative_to(config.data_dir.resolve()) or not proof_path.is_file()
                or digest_file(proof_path) != source['dissemination_evidence_sha256']
                or not source.get('dissemination_reviewed_by')):
            raise ValueError('Fallback historical dissemination needs reviewed archived evidence')
        row = dict(source, filing_id=record_id(source), source_document=source['source_url'],
            _document_attempted=True,
            timing_status='VERIFIED', available_at=cutoff, revision_at=None,
            first_seen_at=datetime.now(timezone.utc).isoformat(), parser_status='NOT_ATTEMPTED',
            source_sha256=source['dissemination_evidence_sha256'], metadata_raw_path=str(proof_path))
        client = OfficialDocumentClient(config, source, issuer_hosts=issuer_hosts)
        acquired += 1
        try:
            frame, findings = archive_filings(client, pd.DataFrame([row]), 'financials', history)
            frame['retrieved_at'] = client.last_response.fetched_at if client.last_response else None
            discovered.append(frame)
            review.extend(findings)
        finally:
            client.close()
    added = pd.concat(discovered, ignore_index=True) if discovered else pd.DataFrame()
    unattempted = added.get('_document_attempted', pd.Series(dtype=bool)).eq(False)
    added = verify_filing_archives(added, config.data_dir)
    if len(added):
        added.loc[unattempted, 'parser_status'] = 'NOT_ATTEMPTED'
        # Separate parser observations from the metadata identity, as in the
        # version store. Never overwrite an already acquired disclosure.
        added['metadata_filing_id'] = added.filing_id
        added['filing_id'] = [record_id(dict(metadata_filing_id=r['filing_id'],
            document_sha256=r.get('document_sha256'))) for r in added.to_dict('records')]
    combined = pd.concat([filings, added], ignore_index=True) if len(added) else filings.copy()
    combined = combined.drop_duplicates('filing_id', keep='first') if len(combined) else combined
    if len(combined) and 'metadata_filing_id' in combined:
        reused = set(combined.loc[combined.document_sha256.notna(), 'metadata_filing_id'].dropna())
        changed_metadata = set(combined.loc[combined.metadata_filing_id.isin(reused)
            & combined.document_sha256.notna()].groupby('metadata_filing_id').document_sha256.nunique().loc[lambda s:s.gt(1)].index)
        if changed_metadata:
            # Changed bytes with the same disclosure identity do not prove the
            # replacement's historical availability. Revoke that identity.
            mask = combined.metadata_filing_id.isin(changed_metadata)
            combined.loc[mask, 'timing_status'] = 'UNCERTAIN_DOCUMENT_REVISION'
            combined.loc[mask, 'document_revision_detected_at'] = datetime.now(timezone.utc).isoformat()
    updated_attempts = dict(attempts)
    for row in added.to_dict('records'):
        if row.get('_document_attempted') is not True:
            continue
        key = row['metadata_filing_id']
        updated_attempts[key] = dict(parser_status=row.get('parser_status'),
            review=[r for r in review if r.get('filing_id') == key])
    options = {k: coverage[k] for k in ('basis', 'max_age_days', 'max_quarter_age_days')}
    audit = audit_fundamental_coverage(universe, combined, sessions,
        start=coverage['periods'][0]['as_of'], end=coverage['periods'][-1]['as_of'],
        attempts=updated_attempts, **options)
    next_ceiling = coverage_ceiling(universe, audit, combined, attempts=updated_attempts)
    next_ledger = build_discovery_gap(universe, audit, next_ceiling, combined)
    plan = plan_acquisition(universe, audit, combined, attempts=updated_attempts)
    write_parquet(added, root/'new-filings.parquet')
    write_parquet(combined, root/'filings.parquet')
    for name, obj in [('coverage', audit), ('coverage-ceiling', next_ceiling),
                      ('discovery-gap', next_ledger), ('acquisition-plan', plan),
                      ('attempts', dict(attempted=updated_attempts))]:
        write_json(root/(name+'.json'), obj)
    report = dict(status='SOURCE_BLOCKED' if errors else 'BATCH_COMPLETE', requests=count,
        completed_queries_skipped=skipped,
        documents_attempted=acquired, new_observations=len(added), selected_cells=len(targets),
        selected_instruments=len(names), responses=responses, errors=errors, review=review,
        missing_cells_before=ledger['missing_cells'], missing_cells_after=next_ledger['missing_cells'],
        requires_replanning_before_next_batch=True, coverage_certified=False,
        performance_used_to_prioritize=False, output=str(root))
    report['output_sha256'] = {p.name: digest_file(p) for p in root.iterdir() if p.is_file()}
    write_json(root/'batch-report.json', report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    for name in ('universe', 'coverage', 'ceiling', 'filings', 'calendar', 'identities', 'corpus-data-dir'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--attempts', type=Path)
    parser.add_argument('--fallback-manifest', type=Path)
    parser.add_argument('--issuer-host', action='append', default=[])
    parser.add_argument('--previous-batch', action='append', type=Path, default=[], help='Verified batch report; supply its combined filings/coverage/ceiling to continue')
    for name, default in [('max-instruments', 25), ('max-cells', 100), ('max-requests', 25), ('max-documents', 25)]:
        parser.add_argument('--'+name, type=int, default=default)
    args = parser.parse_args()
    paths = [args.universe, args.coverage, args.ceiling, args.filings, args.calendar, args.identities]
    paths += [p for p in (args.attempts, args.fallback_manifest) if p]+args.previous_batch
    hashes = {str(p): digest_file(p) for p in paths}
    filings = read_parquet_file(args.filings)
    original = verify_filing_archives(filings, args.corpus_data_dir)
    local = verify_filing_archives(filings, args.config(config).data_dir)
    if len(filings):
        filings.loc[original.parser_status.eq('NEEDS_REVIEW') & local.parser_status.eq('NEEDS_REVIEW'), 'parser_status'] = 'NEEDS_REVIEW'
    completed = []
    for path in args.previous_batch:
        previous = json.loads(path.read_text(encoding='utf-8'))
        for name, expected_hash in previous['output_sha256'].items():
            source = (path.parent/name).resolve()
            if not source.is_relative_to(path.parent.resolve()) or digest_file(source) != expected_hash:
                raise ValueError('Previous discovery batch outputs changed')
        completed.extend(previous['responses'])
    calendar = read_parquet_file(args.calendar)
    report = discover_targeted(args.config(config), read_parquet_file(args.universe),
        json.loads(args.coverage.read_text(encoding='utf-8')), json.loads(args.ceiling.read_text(encoding='utf-8')),
        filings, calendar.loc[calendar.is_trading_session, 'trade_date'], read_parquet_file(args.identities),
        attempts=json.loads(args.attempts.read_text(encoding='utf-8'))['attempted'] if args.attempts else None,
        fallback_manifest=json.loads(args.fallback_manifest.read_text(encoding='utf-8')) if args.fallback_manifest else (),
        issuer_hosts=args.issuer_host, completed_queries=completed,
        max_instruments=args.max_instruments, max_cells=args.max_cells,
        max_requests=args.max_requests, max_documents=args.max_documents)
    if hashes != {str(p): digest_file(p) for p in paths}:
        raise ValueError('Discovery batch input files changed during execution')
    write_json(Path(report['output'])/'input-files.json', hashes)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
