"""Historical range expansion requires a separate, recorded evidence decision."""
from datetime import date
from pathlib import Path
import json
import pandas as pd
from quant.storage.research_store import digest_file


def require_expansion_decision(config, start, *, decision_path=None):
    if start >= date(2024, 1, 1):
        return None
    if start < date(2016, 1, 1):
        raise ValueError('Fundamental acquisition is limited to the declared 2016-present stages')
    target = 2 if start >= date(2020, 1, 1) else 3
    if decision_path is None:
        raise ValueError('Historical expansion requires an explicit decision after the preceding acquisition and coverage gates')
    decision = json.loads(Path(decision_path).read_text(encoding='utf-8'))
    if (decision.get('decision') != 'EXPAND' or decision.get('prior_stage') != target-1
            or decision.get('next_stage') != target or not decision.get('reviewed_by')
            or not decision.get('reviewed_at')):
        raise ValueError('Expansion decision must identify the preceding and next stages and recorded review')
    reviewed = pd.Timestamp(decision['reviewed_at'])
    if reviewed.tzinfo is None or reviewed > pd.Timestamp.now(tz='UTC'):
        raise ValueError('Expansion review requires a past timezone-aware timestamp')
    reports = {}
    for key in ('acquisition_report', 'coverage_report', 'share_report'):
        evidence = decision.get(key, {})
        path = (config.data_dir/evidence.get('path', '')).resolve()
        if (not path.is_relative_to(config.data_dir.resolve()) or not path.is_file()
                or digest_file(path) != evidence.get('sha256')):
            raise ValueError('Expansion certification evidence is missing or changed')
        reports[key] = json.loads(path.read_text(encoding='utf-8'))
    acquisition = reports['acquisition_report']
    if (acquisition.get('status') != 'ALL_CANDIDATES_CLASSIFIED' or acquisition.get('unattempted_in_scope') != 0
            or acquisition.get('stage1_complete') is not True
            or not acquisition.get('candidate_set_sha256')):
        raise ValueError('Previous acquisition stage is incomplete')
    if any(not reports[k].get('reliable_window_established')
           or reports[k].get('minimum_consecutive_monthly_cutoffs', 0) < 12 for k in ('coverage_report', 'share_report')):
        raise ValueError('Previous stage lacks certified monthly filing/share continuity')
    return decision
