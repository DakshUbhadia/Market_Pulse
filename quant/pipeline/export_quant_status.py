"""Sign a narrow status-only projection for the private Next.js console."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

import requests

from quant.data.http import atomic_write
from quant.forward.signal_store import content_hash


def status_payload(current, *, now, test_only=False):
    def report(key):
        return current.get(key, {}).get('report', {})

    rows = {}
    for report_key, fields in (
        ('filing_coverage', ('coverage_pct', 'top_liquidity_coverage_pct', 'filing', 'filingTop100')),
        ('fundamental_coverage_ceiling', ('theoretical_max_coverage', 'theoretical_max_top100_coverage', 'ceiling', 'ceilingTop100')),
        ('share_coverage', ('verified_share_coverage', 'top100_verified_share_coverage', 'shares', 'sharesTop100')),
        ('v2_matrix', ('joint_overall_pct', 'joint_top100_pct', 'joint', 'jointTop100')),
    ):
        overall, liquid, overall_key, liquid_key = fields
        for period in report(report_key).get('periods', []):
            cutoff = period['as_of']
            row = rows.setdefault(cutoff, dict(cutoff=cutoff, filing=None, filingTop100=None,
                ceiling=None, ceilingTop100=None, shares=None, sharesTop100=None, joint=None, jointTop100=None))
            row.update({overall_key: period.get(overall), liquid_key: period.get(liquid)})

    versions = current['versions']
    review = current.get('human_review_status')
    admission = current.get('evaluation_window_admissible')
    readiness = report('latest_certified_session')
    market_session = (readiness.get('latest_session') if readiness.get('status') == 'READY' else None)
    v1 = current.get('V1_BASELINE_STATE', {})
    v2 = current.get('V2_STATE', {})
    capital = report('capital_event_verification')
    source = report('completion_source_pilot')
    joint = report('v2_matrix').get('joint_status')
    result = dict(schemaVersion=1, gitCommit=current['local_commit'],
        asOf=now.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
        marketSession=market_session or current.get('latest_certified_market_session'),
        authority='TEST_ONLY' if test_only else 'STATUS_ONLY',
        validationStatus='BLOCKED' if 'BLOCKED' in (v1.get('status'), v2.get('status')) else 'UNASSESSED',
        archiveReadiness=readiness['status'] if readiness.get('status') in ('READY', 'NOT_READY') else 'UNASSESSED',
        filingSources='SOURCE_LIMITED' if source.get('status') == 'SOURCE_LIMITED' else 'UNASSESSED',
        jointMatrix=joint if joint in ('THRESHOLDS_MET', 'BLOCKED') else 'UNASSESSED',
        humanReview='PENDING' if review == 'PENDING' else 'RESOLVED' if review == 'APPROVED' else 'UNASSESSED',
        fallback='ADMITTED' if admission is True else 'NOT_ADMITTED' if admission is False else 'UNASSESSED',
        implementation='CERTIFIED' if current.get('certificate_applies_to_local_implementation') else 'UNVERIFIED',
        v1Version=versions['MODEL_VERSION'], v2Version=versions['FACTOR_V2_VERSION'],
        featureVersion=versions['FEATURE_VERSION'], costVersion=versions['COST_MODEL_VERSION'],
        evidenceVersion=versions['EVIDENCE_POLICY_VERSION'], sealHash=None,
        inputManifestHash=report('market_input_manifest').get('input_sha256'),
        openIncidents=current.get('incident_ledger', {}).get('unresolved_incidents'),
        discoveryGaps=report('fundamental_discovery_gap').get('missing_cells'),
        capitalCandidates=capital.get('status_counts', {}).get('NEEDS_REVIEW'),
        coverage=[rows[day] for day in sorted(rows)[-120:]])
    return dict(runId=content_hash(result), **result)


def sign_status(payload, key):
    if not re.fullmatch(r'[a-f0-9]{64}', key or ''):
        raise ValueError('QUANT_STATUS_SIGNING_KEY must be 64 lowercase hexadecimal characters')
    data = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    envelope = dict(payload=base64.b64encode(data).decode(), sha256=hashlib.sha256(data).hexdigest(),
        signature=hmac.new(bytes.fromhex(key), data, hashlib.sha256).hexdigest())
    result = json.dumps(envelope, separators=(',', ':')).encode()
    if len(result) > 65_536:
        raise ValueError('Status envelope exceeds the application size limit')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current-status', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--test-only', action='store_true')
    parser.add_argument('--sync-url', help='Explicit HTTPS URL for /api/quant/status/sync')
    args = parser.parse_args()
    if args.sync_url:
        url = urlsplit(args.sync_url)
        if (args.test_only or url.scheme != 'https' or not url.hostname or url.username or url.password
                or url.fragment or url.query or url.path != '/api/quant/status/sync'):
            parser.error('Sync needs a status-only payload and an explicit HTTPS status sync endpoint')
    current = json.loads(args.current_status.read_text(encoding='utf-8'))
    generated = datetime.fromisoformat(current['generated_at'])
    if generated.tzinfo is None:
        raise ValueError('Quant status evidence requires a time zone')
    payload = status_payload(current, now=generated, test_only=args.test_only)
    envelope = sign_status(payload, os.getenv('QUANT_STATUS_SIGNING_KEY'))
    atomic_write(args.output, envelope)
    if args.sync_url:
        token = os.getenv('QUANT_STATUS_SYNC_TOKEN', '')
        if not re.fullmatch(r'[a-f0-9]{64}', token):
            raise ValueError('QUANT_STATUS_SYNC_TOKEN must be 64 lowercase hexadecimal characters')
        response = requests.post(args.sync_url, data=envelope, timeout=15, allow_redirects=False,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
        if response.status_code not in (200, 201):
            raise ValueError(f'Status sync returned HTTP {response.status_code}')
    print(args.output)


if __name__ == '__main__':
    main()
