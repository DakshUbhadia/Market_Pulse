"""Freeze reviewed research policy before evaluating any candidate outcomes."""
from datetime import datetime, timezone
from pathlib import Path
import json

import pandas as pd

from quant.forward.signal_store import append_record, content_hash
from quant.storage.research_store import digest_file
from quant.models.factor_v2 import BLOCKS


def research_code_hashes():
    from quant.config import REPO_ROOT
    return {p.relative_to(REPO_ROOT).as_posix():digest_file(p) for p in (REPO_ROOT/'quant').rglob('*.py')
            if not any(part in ('tests','.venv','__pycache__') for part in p.parts)}


def validate_specification(spec):
    if spec.get('return_basis','PRICE') not in ('PRICE','TOTAL_RETURN'):
        raise ValueError('Unsupported return basis')
    if spec.get('review_status') != 'REVIEWED' or not str(spec.get('reviewed_by') or '').strip():
        raise ValueError('Research specification requires an explicit recorded review')
    if spec.get('block_weights') != {name:1/len(BLOCKS) for name in BLOCKS}:
        raise ValueError('Initial V2 research requires equal declared block weights')
    if spec.get('min_group_size',0)<20:
        raise ValueError('Research normalization needs at least 20 names per entity group')
    windows=spec.get('evaluation_windows',[])
    if not windows:
        raise ValueError('Declare evaluation windows before experiments')
    last=None
    for window in windows:
        start,end=pd.Timestamp(window['from']),pd.Timestamp(window['to'])
        if start>end or (last is not None and start<=last):
            raise ValueError('Evaluation windows must be ordered and nonoverlapping')
        last=end
    required={'min_oos_sessions','min_mean_ic_improvement','min_ir_improvement',
              'max_drawdown_deterioration','max_turnover','min_label_coverage'}
    criteria=spec.get('acceptance',{})
    if set(criteria)!=required or any(not isinstance(v,(int,float)) or not float('-inf')<v<float('inf') for v in criteria.values()):
        raise ValueError('Declare all numerical promotion criteria')
    if (criteria['min_oos_sessions']<504 or min(criteria.values())<0
            or not 0<criteria['min_label_coverage']<=1 or criteria['max_turnover']<=0):
        raise ValueError('Invalid promotion criteria or insufficient declared OOS length')
    return spec


def freeze_specification(spec, output):
    validate_specification(spec)
    body=dict(specification=spec,source_code_sha256=research_code_hashes(),
              frozen_at=datetime.now(timezone.utc).isoformat())
    append_record(Path(output),dict(**body,sha256=content_hash(body)))


def load_specification(path):
    record=json.loads(Path(path).read_text())
    if record.get('sha256')!=content_hash({k:v for k,v in record.items() if k!='sha256'}):
        raise ValueError('Frozen specification checksum changed')
    if record['source_code_sha256']!=research_code_hashes():
        raise ValueError('Research implementation changed after specification freeze; review a new specification')
    return validate_specification(record['specification'])
