"""Archive official TRI history in yearly windows, requiring complete session coverage."""
import json
import time
from datetime import date, datetime, timezone
from uuid import uuid4

import pandas as pd

import requests

from quant.data.http import atomic_write, sha256
from quant.data.nifty_tri import SOURCE_URL, SOURCE_PAGE, BENCHMARKS, parse_tri
from quant.pipeline.update_calendar import read_calendar
from quant.storage.parquet_store import read_parquet_file, write_parquet
from quant.storage.research_store import write_json


def backfill_tri(config, start, end):
    calendar = read_calendar(config, start, end)
    expected = set(calendar.loc[calendar.is_trading_session, 'trade_date'].dt.date)
    blocks = []
    with requests.Session() as session:
        session.headers.update({'User-Agent':config.nse_user_agent, 'Referer':SOURCE_PAGE})
        for year in range(start.year, end.year+1):
            left, right = max(start, date(year,1,1)), min(end, date(year,12,31))
            for name in BENCHMARKS:
                time.sleep(config.request_interval)
                request = dict(cinfo=str(dict(name=name, startDate=left.strftime('%d-%b-%Y'),
                    endDate=right.strftime('%d-%b-%Y'), indexName=name)))
                response = session.post(SOURCE_URL, json=request, timeout=config.timeout, allow_redirects=False)
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
                raw_path = config.data_dir / 'raw/nifty_indices/tri' / f'{stamp}-{uuid4().hex[:8]}.json'
                atomic_write(raw_path, response.content)
                metadata = dict(source_url=SOURCE_URL, source_page=SOURCE_PAGE, request=request,
                    sha256=sha256(response.content), http_status=response.status_code,
                    fetched_at=datetime.now(timezone.utc).isoformat())
                write_json(raw_path.with_suffix('.metadata.json'), metadata)
                response.raise_for_status()
                frame = parse_tri(response.content, name, left, right)
                wanted = {day for day in expected if left <= day <= right}
                if set(frame.trade_date.dt.date) != wanted:
                    raise ValueError(f'{name} TRI calendar coverage mismatch for {year}')
                frame['source_url'] = SOURCE_URL
                frame['source_sha256'] = metadata['sha256']
                frame['raw_path'] = str(raw_path.relative_to(config.data_dir))
                blocks.append(frame)
                print(f'{year}: {name} TRI verified ({len(frame)} sessions)', flush=True)
    frame = pd.concat(blocks, ignore_index=True)
    # Publish the complete requested range as a single file. Preserve old rows
    # outside the refreshed range and archive the previous version before replace.
    path = config.data_dir / 'normalized/index_tri/history.parquet'
    if path.exists():
        old = read_parquet_file(path)
        archive = path.parent / 'history-revisions' / (sha256(path.read_bytes()) + '.bin')
        if not archive.exists():
            atomic_write(archive, path.read_bytes())
        frame = pd.concat([old[~old.trade_date.between(pd.Timestamp(start),pd.Timestamp(end))],frame])
    write_parquet(frame.sort_values(['trade_date','index_name']),path)
    return dict(status='READY', start=str(start), end=str(end), rows=len(frame), source_url=SOURCE_URL)


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.set_defaults(start=date(2015,12,1))
    args = parser.parse_args()
    config = args.config(config)
    try:
        result = backfill_tri(config, args.start, args.end)
    except (OSError, ValueError, requests.RequestException) as error:
        result = dict(status='NOT_READY', error=str(error), source_url=SOURCE_URL)
    write_json(config.data_dir/'reports/tri-coverage.json',result)
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='READY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
