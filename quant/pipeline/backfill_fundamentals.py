"""Bounded, resumable filing discovery with immutable raw financial documents."""
import json
from datetime import timedelta

import pandas as pd

from quant.data.nse_client import NseClient, NseSourceError
from quant.data.nse_financials import PATH, parse_financial_filings
from quant.data.financial_versions import FinancialVersionStore
from quant.pipeline.state import state_lock
from quant.pipeline.update_corporate import windows, archive_filings
from quant.storage.parquet_store import read_parquet_file
from quant.storage.research_store import write_json


def backfill_fundamentals(config, start, end, *, window_days=30, revision_overlap_days=14,
                          refresh=False, client_factory=NseClient, expansion_decision=None):
    if start > end or not 1 <= window_days <= 90 or not 0 <= revision_overlap_days <= 90:
        raise ValueError('Invalid bounded fundamental backfill window or overlap')
    from quant.research.acquisition_stages import require_expansion_decision
    expansion = require_expansion_decision(config, start, decision_path=expansion_decision)
    root = config.data_dir/'state/fundamental_backfill'
    checkpoint_path = root/f'{start}-{end}-{window_days}.json'
    identity_path = config.data_dir/'normalized/security_history/identities.parquet'
    history = read_parquet_file(identity_path) if identity_path.exists() else pd.DataFrame()
    with state_lock(root/'backfill.lock'):
        versions = FinancialVersionStore(config)
        checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else dict(
            start=str(start), end=str(end), window_days=window_days, windows={})
        checkpoint['revision_overlap_days'] = revision_overlap_days
        overlap_start = end-timedelta(days=revision_overlap_days)
        with client_factory(config) as client:
            for begin, stop in windows(start, end, days=window_days):
                key = f'{begin}:{stop}'
                previous = checkpoint['windows'].get(key, {})
                if previous.get('status') == 'COMPLETE' and stop < overlap_start and not refresh:
                    continue
                row = dict(status='STARTED', metadata=[], records_seen=0, needs_review=[])
                checkpoint['windows'][key] = row
                write_json(checkpoint_path, checkpoint)
                try:
                    for period in ('Quarterly', 'Annual'):
                        payload = client.get_json(PATH, params=dict(index='equities',
                            from_date=begin.strftime('%d-%m-%Y'), to_date=stop.strftime('%d-%m-%Y'), period=period),
                            dataset='financial_filings')
                        raw = client.last_response
                        frame = parse_financial_filings(payload, raw)
                        if not frame.empty:
                            frame, review = archive_filings(client, frame, 'financials', history)
                            row['needs_review'].extend(review)
                            for i, filing in frame.iterrows():
                                attachment = filing.get('attachment_url')
                                if not isinstance(attachment, str) or not attachment.strip():
                                    continue
                                try:
                                    client.get_bytes(attachment, dataset='financial_attachments', suffix='bin')
                                    evidence = client.last_response
                                    frame.loc[i, 'attachment_raw_path'] = str(evidence.path)
                                    frame.loc[i, 'attachment_sha256'] = evidence.sha256
                                except (OSError, ValueError, NseSourceError) as error:
                                    row['needs_review'].append(dict(filing_id=filing.filing_id, reason='ATTACHMENT: '+str(error)))
                        versions.publish(frame, raw)
                        row['metadata'].append(dict(period=period, raw_path=str(raw.path), sha256=raw.sha256,
                                                    fetched_at=raw.fetched_at, source_url=raw.source_url))
                        row['records_seen'] += len(frame)
                    row['status'] = 'COMPLETE'
                except (OSError, ValueError, NseSourceError) as error:
                    row.update(status='FAILED', error=str(error))
                write_json(checkpoint_path, checkpoint)
                if row['status'] == 'FAILED':
                    break  # resume starts at this hole, never jumps over it
        report = dict(status='COMPLETE' if all(row.get('status') == 'COMPLETE' for row in checkpoint['windows'].values())
                      and len(checkpoint['windows']) == len(list(windows(start, end, days=window_days))) else 'BLOCKED',
                      checkpoint=str(checkpoint_path), windows=checkpoint['windows'],
                      coverage_status='UNASSESSED_UNIVERSE_COVERAGE_REQUIRED', fundamental_scoring_enabled=False)
        report['expansion_decision'] = expansion
        frame = pd.concat([read_parquet_file(p) for p in (config.data_dir/'normalized/financials').rglob('*.parquet')], ignore_index=True) if any((config.data_dir/'normalized/financials').rglob('*.parquet')) else pd.DataFrame()
        report.update(requested_range=dict(start=str(start),end=str(end)),discovery_windows=len(checkpoint['windows']),
            filings_discovered=sum(r.get('records_seen',0) for r in checkpoint['windows'].values()),
            versions_preserved=frame.filing_id.nunique() if not frame.empty else 0,
            documents_downloaded=frame.document_sha256.nunique() if 'document_sha256' in frame else 0,
            parsed=int(frame.parser_status.eq('PARSED').sum()) if 'parser_status' in frame else 0,
            needs_review=int(frame.parser_status.ne('PARSED').sum()) if 'parser_status' in frame else len(frame),
            timing_verified=int(frame.timing_status.eq('VERIFIED').sum()) if 'timing_status' in frame else 0,
            identity_resolved=int(frame.instrument_id.notna().sum()) if 'instrument_id' in frame else 0,
            count_scope='Discovery counts include repeated metadata; normalized counts cover preserved corpus')
        write_json(config.data_dir/'reports/fundamental-backfill-status.json', report)
        write_json(config.data_dir/'reports/fundamental-backfill.json', report)
        return report


def main():
    from quant.pipeline.cli import parser_config
    from quant.pipeline.check_research_ready import require_research_ready
    parser, config = parser_config(__doc__)
    parser.add_argument('--window-days', type=int, default=30)
    parser.add_argument('--revision-overlap-days', type=int, default=14)
    parser.add_argument('--refresh', action='store_true', help='Revisit all completed windows for older revisions')
    from pathlib import Path
    parser.add_argument('--expansion-decision', type=Path)
    args = parser.parse_args()
    config = args.config(config)
    try:
        require_research_ready(config, args.end, args.start)
        result = backfill_fundamentals(config, args.start, args.end, window_days=args.window_days,
            revision_overlap_days=args.revision_overlap_days, refresh=args.refresh, expansion_decision=args.expansion_decision)
    except (ValueError, OSError) as error:
        result = dict(status='BLOCKED', reason=str(error), fundamental_scoring_enabled=False)
        write_json(config.data_dir/'reports/fundamental-backfill.json', result)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'COMPLETE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
