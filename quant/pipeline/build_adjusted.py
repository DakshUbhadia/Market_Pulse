"""Publish adjusted partitions only after price and corporate coverage pass."""
import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import pandas as pd

from quant.features.adjustments import adjust_prices, action_version
from quant.features.returns import calculate_returns
from quant.pipeline.audit_prices import audit_prices
from quant.pipeline.state import PipelineState
from quant.data.normalization import write_daily
from quant.data.http import atomic_write
from quant.storage.parquet_store import write_parquet
from quant.storage.duckdb_store import query_prices


def action_fingerprints(actions):
    if actions.empty:
        return {}
    keys = actions.instrument_id.astype(object).fillna('SYMBOL:' + actions.symbol)
    return {str(key): action_version(group) for key, group in actions.groupby(keys, sort=False)}


def _incremental_partitions(config, start, end, actions, prior, fingerprints):
    """Rebase changed identities only; normal EOD work reads the overlap window."""
    before = prior.get('action_fingerprints')
    if before is None and prior.get('corporate_action_version') == action_version(actions):
        # An older full build's corpus hash proves these are its exact inputs;
        # initialize per-identity fingerprints without another market-wide rebase.
        before = fingerprints
    if before is None:
        raise ValueError('Adjustment baseline has no event fingerprints; run weekly audit --rebuild-adjusted')
    changed = {key for key in set(before) | set(fingerprints) if before.get(key) != fingerprints.get(key)}
    ids = {key for key in changed if not key.startswith('SYMBOL:')}
    symbols = {key.removeprefix('SYMBOL:') for key in changed if key.startswith('SYMBOL:')}
    if not actions.empty:
        symbols.update(actions.loc[actions.instrument_id.isin(ids), 'symbol'])
    isins = set()
    if ids:
        identities = pd.read_parquet(config.data_dir / 'normalized/security_history/identities.parquet')
        matched = identities[identities.instrument_id.isin(ids)]
        if not ids.issubset(set(matched.instrument_id)):
            raise ValueError('Changed action identity lacks historical ISIN evidence; full rebase required')
        isins.update(matched['isin'].dropna())
    def affected(frame):
        return frame['isin'].isin(isins) | frame.symbol.isin(symbols)
    # Include the preceding session to preserve return continuity at the seam.
    earlier = sorted(path.stem for path in config.prices_dir.rglob('*.parquet') if path.stem < str(start))
    read_start = earlier[-1] if earlier else str(start)
    bars = query_prices(config.prices_dir, start=read_start, end=end)
    recent = calculate_returns(adjust_prices(bars.loc[~affected(bars)], actions)) if (~affected(bars)).any() else pd.DataFrame()
    if not recent.empty:
        recent = recent[pd.to_datetime(recent.trade_date).dt.date >= start]
    rebased = pd.DataFrame()
    if changed:
        files = [str(path) for path in config.prices_dir.rglob('*.parquet')
                 if prior['from'] <= path.stem <= str(end)]
        with duckdb.connect(':memory:') as connection:
            changed_bars = connection.execute('SELECT * FROM read_parquet(?, hive_partitioning=false, union_by_name=true) '
                'WHERE isin IN (SELECT unnest(?)) OR symbol IN (SELECT unnest(?))',
                [files, sorted(isins), sorted(symbols)]).fetchdf()
        if not changed_bars.empty:
            rebased = calculate_returns(adjust_prices(changed_bars, actions))
    historical = rebased[pd.to_datetime(rebased.trade_date).dt.date < start] if not rebased.empty else rebased
    partitions = 0
    root = config.data_dir / 'normalized/adjusted_prices'
    for day, replacement in historical.groupby('trade_date') if not historical.empty else []:
        path = root / f'year={day.year}/month={day.month:02d}/{day:%Y-%m-%d}.parquet'
        old = pd.read_parquet(path)
        combined = pd.concat([old.loc[~affected(old)], replacement], ignore_index=True)
        write_parquet(combined, path)
        partitions += 1
    frames = [recent] if not recent.empty else []
    if not rebased.empty:
        frames.append(rebased[pd.to_datetime(rebased.trade_date).dt.date >= start])
    if frames:
        recent = pd.concat(frames, ignore_index=True)
        partitions += len(write_daily(recent, root))
    excluded = set(prior.get('excluded_symbols', []))
    for frame in (recent, rebased):
        if not frame.empty:
            excluded.update(frame.loc[frame.adjustment_status != 'OK', 'symbol'].dropna())
    return len(recent) + len(historical), partitions, sorted(excluded)


def _build_partitions(config, start, end, actions):
    """Keep a complete identity history together without loading the whole market.

    Disk buckets bound pandas memory; a second disk pass assembles atomic daily
    partitions. Raw archives and the published dataset are never used as scratch.
    """
    scratch = config.data_dir / 'tmp'
    scratch.mkdir(parents=True, exist_ok=True)
    files = [str(path) for path in config.prices_dir.rglob('*.parquet')
             if str(start) <= path.stem <= str(end)]
    rows, excluded, partitions = 0, set(), 0
    with TemporaryDirectory(prefix='adjust-', dir=scratch) as name:
        work = Path(name).resolve()
        if not work.is_relative_to(scratch.resolve()):
            raise ValueError('Adjustment scratch path escaped data directory')
        with duckdb.connect(':memory:') as connection:
            connection.execute("SET threads=1")
            connection.execute("SET memory_limit='512MB'")
            connection.execute("SET temp_directory=?", [str(work / 'spill')])
            connection.execute('COPY (SELECT *, hash(coalesce(nullif(trim(isin), \'\'), symbol)) % 32 AS _bucket '
                'FROM read_parquet(?, hive_partitioning=false, union_by_name=true)) TO ? '
                '(FORMAT PARQUET, PARTITION_BY (_bucket))', [files, str(work / 'raw')])
            output = work / 'adjusted'
            output.mkdir()
            for number, bucket in enumerate(sorted((work / 'raw').iterdir())):
                bars = connection.execute('SELECT * FROM read_parquet(?, hive_partitioning=false, union_by_name=true)',
                                          [[str(path) for path in bucket.glob('*.parquet')]]).fetchdf()
                adjusted = calculate_returns(adjust_prices(bars, actions))
                excluded.update(adjusted.loc[adjusted.adjustment_status != 'OK', 'symbol'].dropna())
                rows += len(adjusted)
                write_parquet(adjusted.sort_values('trade_date'), output / f'{number}.parquet', row_group_size=4096)
                print(f'Adjusted identity bucket {number+1}/32', flush=True)
            # Date-sorted, small row groups permit bounded month reads. A global
            # 8-million-row sort can spill several GB on developer machines.
            month = pd.Timestamp(start).replace(day=1)
            adjusted_files = [str(path) for path in output.glob('*.parquet')]
            while month <= pd.Timestamp(end):
                following = month + pd.offsets.MonthBegin()
                daily = connection.execute('SELECT * FROM read_parquet(?, hive_partitioning=false, union_by_name=true) '
                    'WHERE trade_date >= ? AND trade_date < ?', [adjusted_files, month, following]).fetchdf()
                partitions += len(write_daily(daily, config.data_dir / 'normalized/adjusted_prices'))
                print(f'Published adjusted OHLC {month:%Y-%m}', flush=True)
                month = following
    return rows, partitions, sorted(excluded)


def build_adjusted(config, start, end, *, incremental=False):
    state = PipelineState(config)
    prior = state.data.get('adjusted_prices', {})
    if not incremental and prior.get('from'):
        # Replacing only the recent half of an existing full corpus would leave
        # earlier prices anchored to an incompatible set of future actions.
        start = min(start, date.fromisoformat(prior['from']))
    action_state = state.data.get('nse_corporate_actions', {})
    if (action_state.get('status') != 'READY' or action_state.get('checked_through', '') < str(end)
            or action_state.get('checked_from', '9999-12-31') > str(start)):
        raise ValueError('Corporate-action coverage is incomplete; adjusted research is unavailable')
    if audit_prices(config, start, end)['status'] != 'READY':
        raise ValueError('Price audit must pass before adjusted prices can be generated')
    files = list((config.data_dir / 'normalized' / 'corporate_actions').rglob('*.parquet'))
    actions = pd.concat([pd.read_parquet(path) for path in files], ignore_index=True) if files else pd.DataFrame()
    if not actions.empty:
        actions = actions.drop_duplicates('event_id')
        actions = actions[pd.to_datetime(actions.ex_date).dt.date <= end]
    version = action_version(actions)
    if incremental and prior.get('to', '') > str(end):
        raise ValueError('Incremental adjustments cannot rewind the existing corpus; use a separate research data directory')
    if incremental and prior.get('status') != 'READY':
        raise ValueError('A complete adjustment baseline is required; run weekly audit --rebuild-adjusted')
    fingerprints = action_fingerprints(actions)
    # A failed/partial rebase must revoke readiness before replacing any partition.
    state.record('adjusted_prices', status='BUILDING', day=end)
    try:
        rows, partitions, excluded = (_incremental_partitions(config, start, end, actions, prior, fingerprints)
                                      if incremental else _build_partitions(config, start, end, actions))
    except Exception as error:
        state.record('adjusted_prices', status='FAILED', error=str(error))
        raise
    report = {'status': 'READY', 'rows': rows, 'partitions': partitions,
              'excluded_symbols': excluded,
              'from': str(start), 'to': str(end)}
    report['corporate_action_version'] = version
    report['action_fingerprints'] = fingerprints
    if incremental and prior.get('from'):
        report['from'] = min(prior['from'], report['from'])
    state.record('adjusted_prices', day=end, **report)
    atomic_write(config.data_dir / 'reports' / f'adjustments-{end}.json', json.dumps(report, indent=2).encode())
    return report
