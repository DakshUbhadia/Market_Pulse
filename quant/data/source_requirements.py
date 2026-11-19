"""Dataset requirements, independent of the transport used to obtain them."""
from enum import StrEnum


class SourceClass(StrEnum):
    OFFICIAL_STATIC_ARCHIVE = 'OFFICIAL_STATIC_ARCHIVE'
    OFFICIAL_API = 'OFFICIAL_API'
    ARCHIVED_CHECKSUMMED_SOURCE = 'ARCHIVED_CHECKSUMMED_SOURCE'


PIPELINE_DATASETS = {
    'historical_research': ('sessions', 'prices', 'benchmark', 'identities',
                            'corporate_actions', 'lifecycle', 'security_transitions'),
    'forward_refresh': ('sessions', 'prices', 'benchmark', 'identities',
                        'corporate_actions', 'lifecycle', 'security_transitions'),
    'fundamental_acquisition': ('filing_metadata', 'filing_documents', 'identities'),
    'production_publishing': ('sessions', 'prices', 'benchmark', 'identities',
                             'corporate_actions', 'lifecycle', 'security_transitions',
                             'approved_model', 'monitoring', 'incident_ledger'),
}


def assess_requirements(pipeline, observations, *, required_session=None):
    """Any verified approved source may satisfy a dataset; fail closed on gaps.

    A source observation certifies its own bytes and scope, never a whole API.
    Archival copies additionally require a verified checksum. Operational
    artifacts use the same provenance contract as market datasets.
    """
    if pipeline not in PIPELINE_DATASETS:
        raise ValueError('Unknown pipeline')
    if pipeline in ('forward_refresh', 'production_publishing') and not required_session:
        raise ValueError('A dated session is required for current inputs')
    datasets = {}
    for dataset in PIPELINE_DATASETS[pipeline]:
        accepted = []
        for row in observations:
            if row.get('dataset') != dataset:
                continue
            if (row.get('source_class') not in set(SourceClass) or row.get('status') != 'READY'
                    or row.get('provenance_verified') is not True or not row.get('source_id')):
                continue
            if (row['source_class'] == SourceClass.ARCHIVED_CHECKSUMMED_SOURCE
                    and row.get('checksum_verified') is not True):
                continue
            if (pipeline in ('forward_refresh', 'production_publishing')
                    and row.get('verified_session') != str(required_session)):
                continue
            accepted.append(row['source_id'])
        datasets[dataset] = dict(ready=bool(accepted), accepted_sources=sorted(set(accepted)))
    return dict(pipeline=pipeline, ready=all(r['ready'] for r in datasets.values()),
                required_session=str(required_session) if required_session else None, datasets=datasets)
