"""Publish a short-lived, owner-bound V1 research ranking from verified evidence."""
import argparse
import base64
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import hashlib
import hmac
import json
from math import isfinite
import os
from pathlib import Path
import re

from quant.config import Config
from quant.data.http import atomic_write
from quant.pipeline.export_quant_status import publish_local
from quant.storage.research_store import digest_file

DOMAIN = b'quant/investment/v1\0'
PAGE_SIZE = 50
LIVE_PATHS = dict(window='reports/v1-evaluation-window-admitted.json', calendar='reports/calendar-health.json',
                  pipeline='state/pipeline_state.json')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def signed_manifest(value, key):
    if not re.fullmatch(r'[a-f0-9]{64}', key or ''):
        raise ValueError('A dedicated investment signing key is required')
    raw = canonical(value)
    result = canonical(dict(payload=base64.b64encode(raw).decode(), sha256=hashlib.sha256(raw).hexdigest(),
        signature=hmac.new(bytes.fromhex(key), DOMAIN + raw, hashlib.sha256).hexdigest()))
    if len(result) > 32768:
        raise ValueError('Investment manifest exceeds the size limit')
    return result


def journal_head(root):
    return max(Path(root).glob('*.json'), default=None)


def live_inputs(root):
    governance = journal_head(root/'research/governance/events')
    incidents = journal_head(root/'research/incidents/events') or root/'research/incidents/ledger.json'
    return {k: digest_file(path) for k, path in dict(governance=governance, incidents=incidents,
        **{name: root/file for name, file in LIVE_PATHS.items()}).items()}


def publish_rankings(config, *, output, registry_path, model_id, release, price, total, session, owner, key):
    from quant.config import REPO_ROOT
    from quant.forward.calendar import next_session_open
    from quant.forward.gate import require_completed_baselines
    from quant.governance.gates import GateRegistry
    from quant.models.factor_v1 import WEIGHTS
    from quant.models.registry import ModelRegistry
    from quant.monitoring.incidents import IncidentLedger
    from quant.pipeline.certify_implementation import require_certified_implementation
    from quant.pipeline.check_research_ready import require_research_ready
    from quant.pipeline.cli import completed_day
    from quant.pipeline.run_factor_v1 import run_factor_v1
    from quant.pipeline.update_calendar import read_calendar
    from quant.research.release import verify_research_release
    from quant.version import MODEL_VERSION

    if os.environ.get('QUANT_PRIVATE_RESEARCH_VIEW') != 'true' or not owner:
        raise ValueError('Private research view requires explicit operator authorization and an owner')
    if not re.fullmatch(r'[a-f0-9]{64}', key or '') or key == os.getenv('QUANT_STATUS_SIGNING_KEY'):
        raise ValueError('Configure a distinct investment signing key')
    output = Path(output).resolve()
    if output.is_relative_to((REPO_ROOT/'public').resolve()):
        raise ValueError('Research rankings require private storage')
    gate = GateRegistry(config.data_dir)
    context = gate.require('V1_MODEL_REGISTRATION')
    live_before = live_inputs(config.data_dir)
    registry = ModelRegistry(registry_path)
    registry_head = journal_head(Path(registry_path)/'events')
    registry_digest = digest_file(registry_head)
    entry = registry.snapshot().get(model_id, {})
    if entry.get('state') not in ('HISTORICALLY_VALIDATED', 'FORWARD_CHALLENGER', 'FORWARD_CHAMPION'):
        raise ValueError('Registry has no eligible historically validated model')
    card = registry.card(model_id)
    if card['model_version'] != MODEL_VERSION:
        raise ValueError('Private ranking exporter currently supports certified V1 evidence')
    registry._historical_evidence(card)
    if verify_research_release(release, data_dir=config.data_dir)['model_id'] != model_id:
        raise ValueError('Release does not identify the registered model')
    release_card = json.loads((Path(release)/'model-card.json').read_bytes())
    if release_card['sha256'] != card['sha256']:
        raise ValueError('Release differs from the registry model card')
    baselines = require_completed_baselines(config, price, total)
    if card['historical_completion_sha256'] not in {row['completion_sha256'] for row in baselines.values()}:
        raise ValueError('Release is not bound to the matched V1 baselines')
    certified = require_certified_implementation(config)['RESEARCH_CERTIFIED_SHA']
    if card['git_commit'] != certified:
        raise ValueError('Current implementation differs from the historically validated revision')
    cutoff = completed_day(config)
    calendar = read_calendar(config, session, cutoff)
    eligible = calendar.loc[calendar.is_trading_session, 'trade_date']
    if eligible.empty or eligible.max().date() != session or baselines['PRICE']['date_range']['to'] >= str(session):
        raise ValueError('Ranking requires the current completed session after the historical interval')
    ready = require_research_ready(config, cutoff)
    pipeline = json.loads((config.data_dir/LIVE_PATHS['pipeline']).read_bytes()).get('market_eod', {})
    if (ready.get('latest_session') != str(session) or pipeline.get('status') != 'READY'
            or pipeline.get('last_successful_session') != str(session)):
        raise ValueError('Current-session readiness is missing')
    ledger = IncidentLedger(config.data_dir/'research/incidents')
    assessed = ledger.report(model_id=model_id)
    if assessed['unresolved_incidents'] != 0:
        raise ValueError('Unresolved incidents block rankings')

    ranks, ranked_file = run_factor_v1(config, session)
    feature_manifest = json.loads(ranked_file.with_suffix('.json').read_bytes())['feature_manifest']
    if feature_manifest['git_commit'] != certified or feature_manifest.get('as_of') != str(session):
        raise ValueError('Ranking input does not match the current certified revision and session')
    if not 0 < len(ranks) <= 5000:
        raise ValueError('Ranking universe is invalid or too large')
    rows = []
    for row in ranks.to_dict('records'):
        symbol, identity = row['symbol'], row['instrument_id']
        if (not re.fullmatch(r'[A-Z0-9&.\-]{1,30}', str(symbol))
                or not re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}', str(identity))):
            raise ValueError('Ranking contains an unsupported identity')
        rows.append(dict(instrumentId=str(identity), symbol=str(symbol), rank=int(row['rank']),
            percentile=float(row['percentile_score']), advInr=float(row['adv_60']), volatility=float(row['vol_63']),
            blocks={name: float(row[name + '_score'])*weight for name, weight in WEIGHTS.items()}))
    if len({row['instrumentId'] for row in rows}) != len(rows) or any(
            row['rank'] != index or not 0 <= row['percentile'] <= 100
            or not all(isfinite(row[key]) and row[key] >= 0 for key in ('advInr', 'volatility'))
            for index, row in enumerate(rows, 1)):
        raise ValueError('Ranking rows do not match the certified universe')
    now = datetime.now(timezone.utc)
    next_open, _ = next_session_open(config, session)
    expiry = min(now+timedelta(minutes=30), next_open.to_pydatetime())
    if expiry <= now:
        raise ValueError('Current ranking window has already expired')
    if (journal_head(Path(registry_path)/'events') != registry_head or live_inputs(config.data_dir) != live_before
            or digest_file(registry_head) != registry_digest or ledger.report(model_id=model_id) != assessed
            or gate.require('V1_MODEL_REGISTRATION') != context or completed_day(config) != cutoff):
        raise ValueError('Research admission changed before publication')
    stamp = lambda instant: instant.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
    pages = [rows[offset:offset+PAGE_SIZE] for offset in range(0, len(rows), PAGE_SIZE)]
    record = dict(schemaVersion=1, authority='RESEARCH_RANKINGS', ownerScope=hashlib.sha256(owner.encode()).hexdigest(),
        modelId=model_id, modelVersion=card['model_version'], codeSha=certified, seal=card['historical_completion_sha256'],
        manifest=hashlib.sha256(canonical(feature_manifest)).hexdigest(), gateDecision=hashlib.sha256(canonical(context)).hexdigest(),
        registry=dict(file=registry_head.name, sha256=registry_digest), liveInputs=live_before,
        session=str(session), asOf=stamp(now),
        expiresAt=stamp(expiry), nextOpen=stamp(next_open), size=len(rows),
        proxyCosts=any(r['highest_validation_level'] != 'PRODUCTION_VALIDATED' for r in baselines.values()),
        pages=[hashlib.sha256(canonical(page)).hexdigest() for page in pages])
    record['runId'] = hashlib.sha256(canonical(record)).hexdigest()
    for i, page in enumerate(pages):
        destination = output.with_name(output.name + '.pages') / record['runId'] / f'{i}.json'
        raw_page = canonical(page)
        if len(raw_page) > 65536 or (destination.exists() and destination.read_bytes() != raw_page):
            raise ValueError('An immutable ranking page changed during publication')
        atomic_write(destination, raw_page)
    publish_local(output, signed_manifest(record, key), record)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'registry', 'release', 'price', 'total'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--model-id', required=True)
    parser.add_argument('--as-of', type=date.fromisoformat, required=True)
    args = parser.parse_args()
    try:
        publish_rankings(replace(Config(), data_dir=args.data_dir), output=args.output, registry_path=args.registry,
            model_id=args.model_id, release=args.release, price=args.price, total=args.total, session=args.as_of,
            owner=os.getenv('QUANT_STATUS_OWNER_ID'), key=os.getenv('QUANT_INVESTMENT_SIGNING_KEY'))
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, f'Research ranking blocked: {error}\n')


if __name__ == '__main__':
    main()
