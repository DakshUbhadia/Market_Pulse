"""Count filing versions and usable evidence, including unsupported entity types."""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from quant.data.http import atomic_write

CATEGORIES = ('industrial', 'bank', 'nbfc', 'insurance', 'reit', 'invit', 'other')


def audit_fundamentals(config):
    files = list((config.data_dir / 'normalized/financials').rglob('*.parquet'))
    frame = pd.concat([pd.read_parquet(path) for path in files], ignore_index=True) if files else pd.DataFrame()
    groups = []
    if not frame.empty:
        frame = frame.sort_values('first_seen_at').drop_duplicates('filing_id')
        frame['year'] = pd.to_datetime(frame.period_end).dt.year
        frame['entity_type'] = frame.get('entity_type', pd.Series('other', index=frame.index)).str.lower()
        frame.loc[frame.get('bank', pd.Series(False, index=frame.index)).eq(True), 'entity_type'] = 'bank'
        frame.loc[~frame.entity_type.isin(CATEGORIES), 'entity_type'] = 'other'
        for (year, category), rows in frame.groupby(['year', 'entity_type']):
            parsed = rows.get('parser_status', pd.Series('', index=rows.index)).eq('PARSED')
            timing = rows.timing_status.eq('VERIFIED')
            identity = rows.instrument_id.notna()
            downloaded = rows.get('document_raw_path', pd.Series(None, index=rows.index, dtype=object)).map(
                lambda value: isinstance(value, str) and Path(value).is_file())
            usable = parsed & timing & identity & downloaded
            groups.append(dict(year=int(year), entity_type=category, filings_discovered=len(rows),
                raw_documents_downloaded=int(downloaded.sum()), xbrl_parsed=int(parsed.sum()),
                timing_verified=int(timing.sum()), identity_resolved=int(identity.sum()), usable=int(usable.sum()),
                needs_review=int((~usable).sum()), unsupported_taxonomy=int((downloaded & ~parsed).sum())))
    now = datetime.now(ZoneInfo(config.timezone))
    report = {'generated_at': now.isoformat(), 'year_basis': 'filing period_end; distinct immutable filing versions',
              'unsupported_taxonomy_scope': 'Unparsed downloaded XBRL; includes unsupported or ambiguous contexts requiring review',
              'by_year_and_entity_type': groups,
              'entity_types': list(CATEGORIES), 'fundamental_scoring_enabled': False,
              'total_filings_discovered': sum(row['filings_discovered'] for row in groups)}
    atomic_write(config.data_dir / 'reports' / f'fundamentals-audit-{now:%Y%m%d}.json', json.dumps(report, indent=2).encode())
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    args = parser.parse_args()
    print(json.dumps(audit_fundamentals(args.config(config)), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
