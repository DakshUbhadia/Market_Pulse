"""Allowlisted research metadata for the owner status projection."""
from datetime import date, datetime, timezone
from dataclasses import asdict
import hashlib
import inspect
import io
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from xml.etree import ElementTree

from quant.data.capital_events import EVENT_TYPES
from quant.portfolio.constraints import RiskPolicy


def identifier(value, pattern):
    return value if isinstance(value, str) and re.fullmatch(pattern, value) else None


def count(value):
    return value if type(value) is int and 0 <= value < 2**53 else None


def day(value):
    try:
        return date.fromisoformat(value).isoformat() if len(value) == 10 else None
    except (ValueError, TypeError):
        return None


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo:
            return parsed.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    except (ValueError, TypeError):
        pass
    return None


def project_details(current, status, *, reports, archive, history, current_sha256):
    artifacts = {}
    classes = {
        'current': 'ARCHIVED_INPUT', 'acceptance': 'LOCAL_TEST', 'certificate': 'CERTIFIED_SOFTWARE',
        'refresh': 'ARCHIVED_INPUT', 'smoke': 'LOCAL_TEST', 'pilot': 'ARCHIVED_INPUT',
        'filing': 'ARCHIVED_INPUT', 'ceiling': 'ARCHIVED_INPUT', 'discovery': 'ARCHIVED_INPUT',
        'shares': 'ARCHIVED_INPUT', 'joint': 'ARCHIVED_INPUT', 'interval': 'ARCHIVED_INPUT',
        'capital': 'ARCHIVED_INPUT', 'tidewater': 'ARCHIVED_INPUT', 'fallback': 'ARCHIVED_INPUT',
        'cairn': 'DIAGNOSTIC', 'runs': 'DIAGNOSTIC', 'controlled': 'DIAGNOSTIC',
        'forward': 'TEST_ONLY', 'monitoring': 'TEST_ONLY', 'capitalQueue': 'ARCHIVED_INPUT',
        'riskPolicy': 'CONFIGURED_POLICY', 'priorSmoke': 'LOCAL_TEST',
    }

    def bind(key, digest):
        if identifier(digest, r'[a-f0-9]{64}'):
            artifacts[key] = dict(sha256=digest, evidenceClass=classes[key])

    bind('current', current_sha256)

    def read(key, path, embedded=None):
        try:
            raw = path.read_bytes()
            value = json.loads(raw)
            if isinstance(value, dict):
                bind(key, hashlib.sha256(raw).hexdigest())
                return value
        except (OSError, ValueError):
            pass
        if embedded:
            record = current.get(embedded, {})
            value = record.get('report')
            if isinstance(value, dict) and identifier(record.get('sha256'), r'[a-f0-9]{64}'):
                # The complete source snapshot is bound separately. A missing original
                # file cannot establish its independent digest.
                return value
        return {}

    def p(name):
        return archive / 'reports' / name
    local = read('acceptance', reports / 'acceptance.json')
    certificate = read('certificate', reports / 'implementation-certification.json', 'implementation_certification')
    refresh = read('refresh', reports.parent / 'market-refresh/reports/research-readiness.json')
    smoke = read('smoke', p('source-health-refresh-2026-11-24.json'))
    pilot = read('pilot', reports / 'official-source-pilot.json', 'completion_source_pilot')
    read('filing', reports / 'fundamental-universe-coverage.json', 'filing_coverage')
    ceiling = read('ceiling', reports / 'fundamental-coverage-ceiling.json', 'fundamental_coverage_ceiling')
    discovery = read('discovery', reports / 'fundamental-discovery-gap.json', 'fundamental_discovery_gap')
    read('shares', reports / 'share-history-coverage.json', 'share_coverage')
    joint = read('joint', reports / 'v2-matrix-status.json', 'v2_matrix')
    interval = read('interval', reports / 'v2-data-interval.json', 'v2_data_interval')
    capital = read('capital', reports / 'capital-events-reviewed.json', 'capital_event_verification')
    tidewater = read('tidewater', history / 'reports/security-transitions/tidewater-2016-human-review-packet.json')
    fallback = read('fallback', history / 'reports/v1-evaluation-declaration.json')
    cairn = read('cairn', p('security-transitions/cairn-2017-evidence-gap.json'))
    runs = read('runs', p('diagnostic-v1-summary.json'))
    controlled = read('controlled', p('controlled-diagnostics.json'))
    forward = read('forward', p('test-forward-dry-run.json'))
    monitoring = read('monitoring', p('monitoring-dry-run.json'))

    metrics = {}
    def measure(key, value, artifact, at=None):
        if count(value) is not None:
            metrics[key] = dict(value=value, artifact=artifact if artifact in artifacts else 'current', asOf=at)

    at = timestamp(local.get('recorded_at'))
    software, live, recovery = (local.get(k, {}) for k in ('software', 'live_sources', 'recovery'))
    if software.get('unit_failures') == 0:
        measure('localTestsPassed', software.get('unit_tests'), 'acceptance', at)
    measure('livePassed', live.get('passed'), 'acceptance', at)
    measure('liveFailed', live.get('failed'), 'acceptance', at)
    measure('restoredFiles', recovery.get('restored_release_files'), 'acceptance', at)
    measure('discoveryCells', discovery.get('missing_cells'), 'discovery')
    measure('discoveryInstruments', discovery.get('missing_instruments'), 'discovery')
    failures = [count(row.get('missing_eligible_count')) for row in ceiling.get('periods', [])]
    if failures and all(n is not None for n in failures):
        measure('usabilityCells', sum(failures), 'ceiling')
    measure('capitalCandidates', capital.get('status_counts', {}).get('NEEDS_REVIEW'), 'capital')
    measure('pilotCells', pilot.get('selected_cells'), 'pilot')
    measure('admittedDocuments', pilot.get('admitted_fallback_documents'), 'pilot')
    if type(pilot.get('missing_cells_before')) is int and type(pilot.get('missing_cells_after')) is int:
        measure('verifiedRepairs', pilot['missing_cells_before'] - pilot['missing_cells_after'], 'pilot')
    real_cohorts = current.get('registered_forward_cohorts')
    if isinstance(real_cohorts, list) and (status['authority'] == 'STATUS_ONLY' or not real_cohorts):
        measure('realCohorts', len(real_cohorts), 'current', status['asOf'])

    try:
        raw = p('live-tests-2026-11-24.xml').read_bytes()
        suite = ElementTree.fromstring(raw).find('testsuite')
        if suite is not None:
            failed = int(suite.get('failures', '0')) + int(suite.get('errors', '0'))
            passed = int(suite.attrib['tests']) - failed - int(suite.get('skipped', '0'))
            bind('priorSmoke', hashlib.sha256(raw).hexdigest())
            probe_time = timestamp(suite.get('timestamp'))
            measure('priorLivePassed', passed, 'priorSmoke', probe_time)
            measure('priorLiveFailed', failed, 'priorSmoke', probe_time)
    except (OSError, ElementTree.ParseError, ValueError, KeyError):
        pass

    if (forward.get('cohort_type') == 'TEST_ONLY' and forward.get('real_forward_evidence') is False
            and forward.get('promotion_eligible') is False):
        cutoff = day(forward.get('as_of'))
        for key, field in [('testSignals', 'signal_sessions'), ('shadowObservations', 'shadow_sessions')]:
            measure(key, forward.get(field), 'forward', cutoff)
        for horizon in (21, 63):
            measure(f'matured{horizon}', forward.get('outcomes', {}).get(str(horizon), {}).get('matured_outcomes'), 'forward', cutoff)
    if monitoring.get('cohort_type') == 'TEST_ONLY' and monitoring.get('real_forward_evidence') is False:
        measure('testIncidents', monitoring.get('unresolved_incidents'), 'monitoring', day(monitoring.get('as_of')))
    measure('realIncidents', status.get('openIncidents'), 'current', status['asOf'])

    probe_rows = []
    for source in smoke.get('sources', []):
        if source.get('base_url') in ('https://www.nseindia.com', 'https://www.nseindia.in'):
            probe_rows.append(dict(route=source['base_url'][8:], asOf=timestamp(source.get('checked_at')),
                httpStatus=count(source.get('http_status')), state='BLOCKED' if source.get('status') == 'SOURCE_BLOCKED' else 'UNASSESSED'))
    for source in pilot.get('probes', []):
        try:
            host = identifier(urlsplit(source.get('url', '')).hostname, r'[a-z0-9.-]{1,80}')
        except (ValueError, TypeError, AttributeError):
            continue
        if host:
            probe_rows.append(dict(route=host, asOf=timestamp(source.get('retrieved_at')),
                httpStatus=count(source.get('http_status')), state='BLOCKED' if source.get('state') == 'SOURCE_LIMITED' else 'UNASSESSED'))

    joint_rows = []
    for row in joint.get('periods', [])[-120:]:
        overall, top = row.get('overall', {}), row.get('top100', {})
        values = [count(overall.get('joint')), count(overall.get('eligible')), count(top.get('joint')), count(top.get('eligible'))]
        cutoff = day(row.get('as_of'))
        if cutoff and None not in values and values[0] <= values[1] and values[2] <= values[3]:
            joint_rows.append(dict(cutoff=cutoff, complete=values[0], eligible=values[1],
                topComplete=values[2], topEligible=values[3], valueMissing=count(row.get('verified_value_missing'))))
    sessions = sorted({row['cutoff'] for row in status['coverage']})
    if sessions:
        for k in ('discoveryCells', 'discoveryInstruments', 'usabilityCells'):
            if k in metrics:
                metrics[k]['asOf'] = sessions[-1]

    attempts = []
    for row in runs.get('attempts', []):
        if (row.get('research_authority') == 'DIAGNOSTIC_ONLY' and row.get('outcome') == 'BLOCKED_BY_DATA'
                and row.get('return_basis') in ('PRICE', 'TOTAL_RETURN')
                and identifier(row.get('experiment_id'), r'[0-9]{8}T[0-9]{6}-[a-f0-9]{8}')):
            attempts.append(dict(id=row['experiment_id'], basis=row['return_basis'],
                start=day(row.get('effective_start')), end=day(row.get('requested_end')),
                codeSha=identifier(row.get('implementation_sha'), r'[a-f0-9]{40}'),
                manifest=identifier(row.get('prepared_manifest_input_sha256'), r'[a-f0-9]{64}'),
                outcomeHash=identifier(row.get('experiment_outcome_sha256'), r'[a-f0-9]{64}')))
    gap_rows = []
    for row in discovery.get('cells', [])[:36]:
        symbol = identifier(row.get('symbol'), r'[A-Z0-9&.-]{1,30}')
        cutoff = day(row.get('as_of'))
        if symbol and cutoff:
            period = day(row.get('required_period_end'))
            known_by = timestamp(row.get('latest_acceptable_dissemination'))
            gap_rows.append(dict(symbol=symbol, cutoff=cutoff, period=period, knownBy=known_by,
                candidate=row.get('candidate_present') is True, top100=row.get('top100') is True))

    capital_rows = []
    expected = identifier(capital.get('output_sha256'), r'[a-f0-9]{64}')
    if expected:
        import pyarrow.parquet as pq
        path = reports / 'capital-events-reviewed.parquet'
        try:
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() == expected:
                columns = ['capital_event_id', 'instrument_id', 'event_type', 'effective_date', 'announced_at',
                    'source_sha256', 'verification_status', 'verification_missing_facts', 'security_lineage_id']
                sample = next(pq.ParquetFile(io.BytesIO(data)).iter_batches(batch_size=24, columns=columns), None)
                for row in sample.to_pylist() if sample is not None else []:
                    event_id = identifier(row['capital_event_id'], r'[a-f0-9]{64}')
                    instrument = identifier(row['instrument_id'], r'[a-f0-9-]{36}')
                    if not event_id or not instrument:
                        continue
                    facts = json.loads(row['verification_missing_facts'] or '[]')
                    allowed = ('announced_at', 'credit_date', 'effective_date', 'event_type', 'instrument_id', 'known_at',
                        'listing_date', 'record_date', 'security_lineage_id', 'share_multiplier', 'source_bytes',
                        'valid_dates', 'shares_added', 'shares_removed', 'paid_up_capital_before', 'paid_up_capital_after',
                        'face_value_before', 'face_value_after')
                    capital_rows.append(dict(id=event_id, instrument=instrument,
                        event=row['event_type'] if row['event_type'] in EVENT_TYPES else 'OTHER',
                        state=row['verification_status'] if row['verification_status'] in
                        ('CANDIDATE','TERMS_VERIFIED','DATES_VERIFIED','VERIFIED_COMPLETE','REJECTED','NEEDS_REVIEW') else 'UNASSESSED',
                        effective=day(str(row['effective_date'])[:10]), known=timestamp(str(row['announced_at'])),
                        source=identifier(row['source_sha256'], r'[a-f0-9]{64}'),
                        lineage=bool(identifier(row['security_lineage_id'], r'[a-f0-9-]{36}')),
                        missing=[key for key in allowed if key in facts]))
                bind('capitalQueue', expected)
        except (OSError, ValueError, KeyError, TypeError):
            capital_rows = []

    risk_policy = asdict(RiskPolicy())
    # Bind the executed policy implementation without exposing its path.
    bind('riskPolicy', hashlib.sha256(Path(inspect.getfile(RiskPolicy)).read_bytes()).hexdigest())
    case = tidewater.get('automated_audit', {})
    certified_sha = certificate.get('RESEARCH_CERTIFIED_SHA') if certificate.get('status') == 'CERTIFIED' else None
    return dict(artifacts=artifacts, metrics=metrics, jointCounts=joint_rows, probes=probe_rows[:16],
        filingQueue=gap_rows, capitalQueue=capital_rows, runs=attempts[:20], riskPolicy=risk_policy,
        fallbackStart=day(fallback.get('effective_start')),
        tidewaterAudit=identifier(tidewater.get('canonical_automated_audit_sha256'), r'[a-f0-9]{64}'),
        tidewaterExhausted=case.get('conclusion') == 'EVIDENCE_EXHAUSTED_UNRESOLVED',
        cairnObserved=day(cairn.get('observed_block_date')) if cairn.get('subject_id') == 'CAIRN_2017' else None,
        fourArmDiagnostic=controlled.get('four_arms_exercised') is True and controlled.get('historical_validation') is False,
        continuousJoint=interval.get('certified') is True and joint.get('joint_status') == 'THRESHOLDS_MET',
        eod='BLOCKED' if refresh.get('status') == 'NOT_READY' else 'UNASSESSED',
        scheduler='ACCESS_DENIED' if recovery.get('windows_schedule') == 'ACCESS_DENIED' else 'UNASSESSED',
        certifiedSha=identifier(certified_sha, r'[a-f0-9]{40}'),
        riskVersion=identifier(current.get('versions', {}).get('PORTFOLIO_RISK_VERSION'), r'[a-zA-Z0-9_.-]{1,64}'),
        accountingVersion=identifier(current.get('versions', {}).get('PORTFOLIO_ACCOUNTING_VERSION'), r'[a-zA-Z0-9_.-]{1,64}'))
