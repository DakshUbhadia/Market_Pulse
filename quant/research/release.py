"""Portable research evidence with original seals and byte-level verification."""
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import tempfile

from quant.backtest.artifacts import verify_backtest_seal
from quant.forward.signal_store import append_record, content_hash
from quant.models.model_card import verify_model_card
from quant.models.registry import ModelRegistry
from quant.storage.research_store import digest_file, write_json


def _json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _copy(source, destination):
    if source.is_symlink():
        raise ValueError('Release artifacts must be regular immutable files')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def build_research_release(registry_root, model_id, output, *, specification=None):
    registry = ModelRegistry(registry_root)
    state = registry.snapshot().get(model_id, {}).get('state')
    if state not in ('HISTORICALLY_VALIDATED', 'FORWARD_CHALLENGER', 'FORWARD_CHAMPION'):
        raise ValueError('Research release requires a historically validated candidate')
    card = registry.card(model_id)
    from quant.governance.gates import GateRegistry, data_root_for
    GateRegistry(data_root_for(registry_root)).require('V1_MODEL_REGISTRATION' if
        str(card['model_version']).startswith('factor_v1') else 'V2_PROMOTION')
    registry._historical_evidence(card)
    source = Path(card['historical_experiment']).resolve()
    seal = verify_backtest_seal(source)
    config = _json(source/'config.json')
    spec = _json(Path(specification)) if specification else config.get('specification')
    if spec is None and (source/'specification.json').is_file():
        spec = _json(source/'specification.json')
    if isinstance(spec, dict) and 'specification' in spec:
        spec = spec['specification']
    if spec is None or content_hash(spec) != card['spec_hash']:
        raise ValueError('Release specification must match the immutable model card')
    output = Path(output).resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('Release destination must be new and outside the experiment')
    is_v2 = (source/'v2-decision.json').exists()
    if is_v2 and not all((source/n).is_file() for n in ('filing-coverage.json', 'share-history-coverage.json')):
        raise ValueError('V2 release requires sealed filing and share coverage evidence')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Staging remains inspectable on failure; never publish an incomplete release.
    staging = Path(tempfile.mkdtemp(prefix=output.name+'.pending-', dir=output.parent))
    write_json(staging/'model-card.json', card)
    write_json(staging/'specification.json', spec)
    _copy(source/'completion.json', staging/'completion.json')
    write_json(staging/'input-manifest.json', config.get('manifest', {k: config[k] for k in ('files',) if k in config}))
    supplemental = {}
    for original, expected in config.get('extra_input_sha256', {}).items():
        path = Path(original)
        if not path.is_file() or digest_file(path) != expected:
            raise ValueError('Supplemental research input is missing or changed')
        relative = 'supplemental-inputs/'+expected+path.suffix
        _copy(path, staging/relative)
        supplemental[original] = dict(path=relative, sha256=expected)
    write_json(staging/'supplemental-inputs.json', supplemental)
    for target, original in [('coverage.json', 'filing-coverage.json'), ('share-coverage.json', 'share-history-coverage.json')]:
        if (source/original).exists():
            _copy(source/original, staging/target)
        else:
            write_json(staging/target, dict(status='NOT_APPLICABLE', reason='Price-only V1 has no fundamental/value dependency'))
    metrics = {p.relative_to(source).as_posix(): _json(p) for p in sorted(source.rglob('metrics.json'))}
    if not metrics:
        raise ValueError('A research release requires sealed performance metrics')
    write_json(staging/'metrics.json', metrics)
    for name in ('factor-evidence', 'risk-evidence'):
        (staging/name).mkdir()
    for path in sorted(source.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        _copy(path, staging/'source-experiment'/relative)
        if ('factor-' in path.name or path.stem in ('ic', 'deciles', 'block-missingness')):
            _copy(path, staging/'factor-evidence'/relative)
        if ('risk-' in path.name or path.name in ('capacity-scenarios.json', 'target-orders.parquet', 'cost-stress.json')):
            _copy(path, staging/'risk-evidence'/relative)
    dependencies = config.get('manifest', {}).get('dependencies', {})
    installed = sorted(f'{d.metadata["Name"]}=={d.version}' for d in importlib.metadata.distributions())
    (staging/'environment.txt').write_text(
        'Packaging Python: '+platform.python_version()+'\nHistorical manifest dependencies: '+json.dumps(dependencies, sort_keys=True)
        +'\nPackaging environment (historical versions are in input-manifest.json):\n'+'\n'.join(installed)+'\n', encoding='utf-8')
    if verify_backtest_seal(source) != seal:
        raise ValueError('Original experiment changed while packaging')
    checksums = {p.relative_to(staging).as_posix(): digest_file(p) for p in sorted(staging.rglob('*')) if p.is_file()}
    append_record(staging/'checksums.json', dict(version='research_release_1.0.0', files=checksums,
                                                sha256=content_hash(checksums)))
    verify_research_release(staging)
    os.rename(staging, output)
    return output


def verify_research_release(root, *, data_dir=None):
    root = Path(root).resolve()
    record = _json(root/'checksums.json')
    if record.get('version') != 'research_release_1.0.0':
        raise ValueError('A DIAGNOSTIC_RELEASE cannot be verified as accepted research')
    files = record.get('files', {})
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != root/'checksums.json'}
    if set(files) != actual or record.get('sha256') != content_hash(files):
        raise ValueError('Release artifact set or checksum manifest changed')
    for name, expected in files.items():
        path = root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root) or digest_file(path) != expected:
            raise ValueError('Release artifact checksum changed')
    card = verify_model_card(_json(root/'model-card.json'))
    source = root/'source-experiment'
    verify_backtest_seal(source)
    if (digest_file(root/'completion.json') != card['historical_completion_sha256']
            or digest_file(source/'completion.json') != card['historical_completion_sha256']
            or content_hash(_json(root/'specification.json')) != card['spec_hash']
            or content_hash(_json(root/'input-manifest.json')) != card['data_manifest_hash']):
        raise ValueError('Release provenance differs from the immutable model card')
    config = _json(source/'config.json')
    supplemental = _json(root/'supplemental-inputs.json')
    if {name: row['sha256'] for name, row in supplemental.items()} != config.get('extra_input_sha256', {}):
        raise ValueError('Supplemental input manifest differs from the sealed experiment')
    for row in supplemental.values():
        path = (root/row['path']).resolve()
        if not path.is_relative_to(root) or digest_file(path) != row['sha256']:
            raise ValueError('Supplemental research input checksum changed')
    is_v2 = (source/'v2-decision.json').is_file()
    expected = 'GO_FURTHER_V2_RESEARCH' if is_v2 else 'GO_FURTHER_V1_RESEARCH'
    decision = _json(source/('v2-decision.json' if is_v2 else 'v1-decision.json'))
    if config.get('git_commit') != card['git_commit'] or decision.get('decision') != expected or card['decision'] != 'PASS':
        raise ValueError('Release requires passing historical evidence at the model SHA')
    if data_dir is not None:
        base = Path(data_dir).resolve()
        for item in _json(root/'input-manifest.json').get('files', []):
            path = (base/item['path']).resolve()
            if not path.is_relative_to(base) or not path.is_file() or digest_file(path) != item['sha256']:
                raise ValueError('Immutable source dataset is missing or changed')
    return dict(status='VERIFIED', model_id=card['model_id'], files=len(files),
                external_inputs_verified=data_dir is not None, automatic_promotion=False)


def build_diagnostic_release(source, output):
    """Portable diagnostic bytes; no model card, accepted seal or promotion path."""
    from quant.backtest.artifacts import verify_diagnostic_completion
    from quant.governance.gates import GATE_ID
    source, output = Path(source).resolve(), Path(output).resolve()
    completion = verify_diagnostic_completion(source)
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('Diagnostic release destination must be new and outside the source')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=output.name+'.pending-', dir=output.parent))
    for path in sorted(source.rglob('*')):
        if path.is_file():
            _copy(path, staging/'source-experiment'/path.relative_to(source))
    metadata = dict(release_type='DIAGNOSTIC_RELEASE', research_authority='DIAGNOSTIC_ONLY',
        historical_validation=False, promotion_eligible=False, real_forward_evidence=False,
        governance_block=GATE_ID, governance_status=completion['governance_status'],
        diagnostic_completion_sha256=digest_file(source/'diagnostic-completion.json'))
    write_json(staging/'diagnostic-release.json', metadata)
    write_json(staging/'environment.json', dict(python=platform.python_version(), dependencies=sorted(
        f'{d.metadata["Name"]}=={d.version}' for d in importlib.metadata.distributions())))
    if verify_diagnostic_completion(source) != completion:
        raise ValueError('Diagnostic inputs changed while packaging')
    files = {p.relative_to(staging).as_posix(): digest_file(p) for p in sorted(staging.rglob('*')) if p.is_file()}
    append_record(staging/'checksums.json', dict(version='diagnostic_release_1.0.0', files=files, sha256=content_hash(files)))
    verify_diagnostic_release(staging)
    os.rename(staging, output)
    return output


def verify_diagnostic_release(root):
    from quant.backtest.artifacts import verify_diagnostic_completion
    root = Path(root).resolve()
    record = _json(root/'checksums.json')
    files = record.get('files', {})
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != root/'checksums.json'}
    if (record.get('version') != 'diagnostic_release_1.0.0' or set(files) != actual
            or record.get('sha256') != content_hash(files)):
        raise ValueError('Diagnostic release inventory changed')
    for name, expected in files.items():
        path = (root/name).resolve()
        if not path.is_relative_to(root) or path.is_symlink() or digest_file(path) != expected:
            raise ValueError('Diagnostic release checksum changed')
    metadata = _json(root/'diagnostic-release.json')
    completion = verify_diagnostic_completion(root/'source-experiment')
    if (metadata.get('release_type') != 'DIAGNOSTIC_RELEASE'
            or any(metadata.get(k) is not False for k in ('historical_validation', 'promotion_eligible', 'real_forward_evidence'))
            or metadata.get('diagnostic_completion_sha256') != digest_file(root/'source-experiment/diagnostic-completion.json')
            or completion['governance_status'] != metadata.get('governance_status')
            or (root/'model-card.json').exists()):
        raise ValueError('Diagnostic release cannot claim historical validation or promotion eligibility')
    return dict(status='VERIFIED_DIAGNOSTIC_RELEASE', **metadata, files=len(files))
