"""Verify reviewed capital-event facts against archived official source bytes."""
import json
from pathlib import Path

import pandas as pd

from quant.data.capital_events import ALIASES, EVENT_TYPES, present, replay_capital_event
from quant.data.official_filing_sources import validate_official_source
from quant.storage.research_store import digest_file, write_json
from quant.storage.parquet_store import read_parquet_file, write_parquet

STATUSES = ('CANDIDATE', 'TERMS_VERIFIED', 'DATES_VERIFIED', 'VERIFIED_COMPLETE', 'REJECTED', 'NEEDS_REVIEW')
ISSUANCES = {'BONUS', 'RIGHTS_ISSUE', 'PUBLIC_ISSUE', 'PRIVATE_PLACEMENT', 'ESOP_ISSUANCE',
             'MERGER_CONVERSION', 'DEMERGER_ALLOCATION'}


def verify_capital_events(events, data_dir, *, issuer_hosts=()):
    result = events.copy()
    if 'verification_status' not in result:
        result['verification_status'] = pd.Series('CANDIDATE', index=result.index, dtype=object)
    base = Path(data_dir).resolve()
    for i, row in result.iterrows():
        if row.get('verification_status') == 'REJECTED':
            continue
        kind = ALIASES.get(row.get('event_type'), row.get('event_type'))
        evidence = row.get('event_evidence')
        if isinstance(evidence, str):
            evidence = json.loads(evidence)
        if not isinstance(evidence, dict):
            evidence = {}
        missing = []

        def proven(field):
            proof = evidence.get(field, {})
            try:
                validate_official_source(proof, issuer_hosts=issuer_hosts)
                path = (base/proof['raw_path']).resolve()
                value = row.get(field)
                valid = (proof.get('review_status') == 'VERIFIED' and bool(proof.get('reviewed_by'))
                    and present(value) and str(proof.get('value')) == str(value)
                    and path.is_relative_to(base) and path.is_file()
                    and digest_file(path) == proof.get('source_sha256'))
            except (ValueError, KeyError, TypeError, OSError):
                valid = False
            if not valid:
                missing.append(field)
            return valid

        terms = kind in EVENT_TYPES and kind != 'OTHER' and proven('event_type')
        term_fields = [k for k in ('share_multiplier', 'shares_added', 'shares_removed') if present(row.get(k))]
        terms = bool(term_fields) and all([proven(k) for k in term_fields]) and terms
        try:
            # Verify the disclosed operation here. Actual before/after amounts
            # are reconciled to anchors by the share-chain verifier, separately.
            trial = {k: v for k, v in row.items() if k not in ('shares_after',
                'paid_up_capital_before', 'paid_up_capital_after', 'face_value_before', 'face_value_after')}
            removed = float(row.get('shares_removed', 0)) if present(row.get('shares_removed')) else 0
            replay_capital_event(max(1., removed+1), dict(trial, event_type=kind))
        except (ValueError, TypeError, KeyError):
            terms = False
            missing.append('valid_share_arithmetic')
        date_fields = ['announced_at', 'effective_date']
        if kind in {'SPLIT', 'BONUS', 'RIGHTS_ISSUE', 'BUYBACK', 'CAPITAL_REDUCTION', 'FACE_VALUE_CHANGE'}:
            date_fields.append('record_date')
        if kind in ISSUANCES:
            date_fields += ['credit_date', 'listing_date']
        dates = all([proven(k) for k in date_fields])
        try:
            stamps = [pd.Timestamp(row.get(k)) for k in date_fields]
            if any(pd.isna(t) for t in stamps) or stamps[0].tzinfo is None:
                raise ValueError('Missing dated announcement availability')
            if stamps[0].tz_convert('Asia/Kolkata').date() > pd.Timestamp(row['effective_date']).date():
                raise ValueError('Announcement follows effective date')
            if kind in ISSUANCES:
                credit, listing = pd.Timestamp(row['credit_date']), pd.Timestamp(row['listing_date'])
                if listing < credit or (present(row.get('record_date')) and credit < pd.Timestamp(row['record_date'])):
                    raise ValueError('Capital credit/listing dates are inconsistent')
        except (ValueError, TypeError):
            dates = False
            missing.append('valid_dates')
        lineage = all([proven('security_lineage_id'), proven('instrument_id')])
        # The source used by downstream archive checks must itself be verified.
        raw = (base/str(row.get('raw_path'))).resolve()
        archived = raw.is_relative_to(base) and raw.is_file() and digest_file(raw) == row.get('source_sha256')
        status = ('VERIFIED_COMPLETE' if terms and dates and lineage and archived else
                  'DATES_VERIFIED' if dates else 'TERMS_VERIFIED' if terms else
                  'NEEDS_REVIEW' if evidence or row.get('verification_status') != 'CANDIDATE' else 'CANDIDATE')
        result.loc[i, 'verification_status'] = status
        if status == 'VERIFIED_COMPLETE':
            result.loc[i, 'candidate_only'] = False
        result.loc[i, 'verification_missing_facts'] = json.dumps(sorted(set(missing + ([] if archived else ['source_bytes']))))
    return result


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--events', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--issuer-host', action='append', default=[])
    args = parser.parse_args()
    events = verify_capital_events(read_parquet_file(args.events), args.config(config).data_dir,
                                   issuer_hosts=args.issuer_host)
    write_parquet(events, args.output)
    report = dict(rows=len(events), status_counts=events.verification_status.value_counts().to_dict(),
        input_sha256=digest_file(args.events), output_sha256=digest_file(args.output),
        complete_chains_certified=False)
    write_json(args.output.with_suffix('.json'), report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
