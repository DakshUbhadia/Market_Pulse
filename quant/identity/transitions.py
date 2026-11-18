"""Normalized, evidence-backed security transitions. No inferred identity links."""
from pathlib import Path
from urllib.parse import urlsplit
import numpy as np
import pandas as pd
from quant.storage.research_store import digest_file

TRANSITION_VERSION = 'security_transitions_1.0.0'
TYPES = set('FACE_VALUE_SPLIT BONUS SPLIT_AND_BONUS SECURITY_ISIN_REPLACEMENT MERGER_CONVERSION DEMERGER_CONVERSION CAPITAL_REORGANIZATION SYMBOL_CHANGE_SAME_SECURITY OTHER'.split())
LEVELS = set('VERIFIED_COMPLETE VERIFIED_TERMS_ONLY PARTIALLY_VERIFIED NEEDS_REVIEW REJECTED'.split())
COLUMNS = ('transition_id predecessor_instrument_id successor_instrument_id predecessor_isin successor_isin '
    'security_lineage_id transition_type announced_at ex_date record_date effective_date credit_date listing_date '
    'first_tradable_date raw_share_multiplier economic_share_multiplier price_adjustment_multiplier '
    'source_exchange source_url source_sha256 raw_path verification_status evidence_notes parser_version').split()


def validate_transitions(frame, data_dir=None):
    if frame is None or frame.empty:
        return pd.DataFrame(columns=COLUMNS)
    missing = set(COLUMNS)-set(frame)
    if missing:
        raise ValueError(f'Missing transition fields: {sorted(missing)}')
    rows = frame.copy()
    if rows.transition_id.isna().any() or rows.transition_id.duplicated().any():
        raise ValueError('Ambiguous transition IDs')
    if not rows.transition_type.isin(TYPES).all() or not rows.verification_status.isin(LEVELS).all():
        raise ValueError('Unknown transition type or verification level')
    # Naive timestamps cannot establish information availability.
    for value in rows.announced_at.dropna():
        if pd.Timestamp(value).tzinfo is None:
            raise ValueError('Transition announcement requires an explicit timezone')
    rows['announced_at'] = pd.to_datetime(rows.announced_at, utc=True)
    for key in ('ex_date','record_date','effective_date','credit_date','listing_date','first_tradable_date'):
        rows[key] = pd.to_datetime(rows[key])
    complete = rows[rows.verification_status.eq('VERIFIED_COMPLETE')]
    if complete.predecessor_instrument_id.duplicated().any():
        raise ValueError('Multiple successor legs require separately reviewed allocation accounting')
    for row in complete.to_dict('records'):
        for key in ('predecessor_instrument_id','successor_instrument_id','predecessor_isin','successor_isin',
                    'security_lineage_id','source_exchange','source_url','source_sha256','raw_path','evidence_notes','parser_version'):
            if not isinstance(row[key], str) or not row[key].strip():
                raise ValueError(f'Complete transition requires {key}')
        for key in ('announced_at','ex_date','effective_date','credit_date','listing_date','first_tradable_date'):
            if pd.isna(row[key]):
                raise ValueError(f'Complete transition requires {key}')
        for key in ('raw_share_multiplier','economic_share_multiplier','price_adjustment_multiplier'):
            if not np.isfinite(row[key]) or row[key] <= 0:
                raise ValueError('Invalid transition multiplier')
        if not np.isclose(row['raw_share_multiplier'], row['economic_share_multiplier']):
            raise ValueError('Unequal raw/economic entitlement needs allocation accounting')
        if not np.isclose(row['price_adjustment_multiplier']*row['economic_share_multiplier'], 1):
            raise ValueError('Inconsistent share/price multipliers')
        if row['transition_type'] in ('DEMERGER_CONVERSION','CAPITAL_REORGANIZATION','OTHER'):
            raise ValueError('Complex allocation requires reviewed multi-leg accounting')
        if row['first_tradable_date'] < max(row['credit_date'],row['listing_date'],row['effective_date']):
            raise ValueError('Cannot trade before credit, listing or effectiveness')
        if row['announced_at'].tz_convert('Asia/Kolkata').tz_localize(None).normalize() > row['ex_date']:
            raise ValueError('Retrospective terms cannot authorize historical conversion')
        url = urlsplit(row['source_url'])
        if url.scheme != 'https' or not url.hostname:
            raise ValueError('Evidence requires HTTPS provenance')
        if data_dir is None:
            raise ValueError('Complete transitions require archived evidence verification')
        root = Path(data_dir).resolve()
        path = (root/row['raw_path']).resolve()
        if not path.is_relative_to(root) or not path.is_file() or digest_file(path) != row['source_sha256']:
            raise ValueError('Transition evidence missing or changed')
    # Reject cycles and inconsistent lineage assignments, including disconnected conflicting claims.
    assignments, edges = {}, {}
    for row in complete.to_dict('records'):
        a, b, lineage = row['predecessor_instrument_id'],row['successor_instrument_id'],row['security_lineage_id']
        for identity in (a,b):
            if identity in assignments and assignments[identity] != lineage:
                raise ValueError('Conflicting lineage assignment')
            assignments[identity] = lineage
        if a != b:
            edges[a] = b
    for identity in edges:
        visited = set()
        while identity in edges:
            if identity in visited:
                raise ValueError('Cyclic security lineage')
            visited.add(identity)
            identity = edges[identity]
    return rows.sort_values(['ex_date','transition_id'])


def load_transitions(config):
    from quant.storage.duckdb_store import dataset_files
    from quant.storage.parquet_store import read_parquet_file
    files = dataset_files(config.data_dir,'security_transitions')
    return validate_transitions(pd.concat([read_parquet_file(p) for p in files], ignore_index=True)
        if files else None, config.data_dir)
