"""Consistent command options and conservative EOD availability cutoff."""
import argparse
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from quant.config import Config


def completed_day(config, now=None):
    now = now or datetime.now(ZoneInfo(config.timezone))
    now = now.astimezone(ZoneInfo(config.timezone))
    # 18:30 is an archive-availability cutoff; special sessions still come from the calendar.
    return now.date() if now.time() >= time(18, 30) else now.date() - timedelta(days=1)


def require_history_gate(config, start, end):
    if start < date(2018, 1, 1):
        from quant.pipeline.audit_prices import audit_prices
        target = end if end >= date(2018, 1, 1) else completed_day(config)
        if audit_prices(config, date(2018, 1, 1), target, write=False)['status'] != 'READY':
            raise ValueError('2018-present price history must pass audit before extending to 2010')


def parser_config(description):
    config = Config()
    parser = QuantParser(description=description, config=config)
    parser.add_argument('--from', dest='start', type=date.fromisoformat, default=date(2018, 1, 1))
    parser.add_argument('--to', dest='end', type=date.fromisoformat, default=completed_day(config))
    parser.add_argument('--data-dir', type=Path)
    return parser, config


class QuantArguments(argparse.Namespace):
    def config(self, config):
        return replace(config, data_dir=self.data_dir) if self.data_dir else config


class QuantParser(argparse.ArgumentParser):
    def __init__(self, *, config, **kwargs):
        super().__init__(**kwargs)
        self.quant_config = config

    def parse_args(self, args=None, namespace=None):
        result = super().parse_args(args, namespace or QuantArguments())
        if result.start > result.end:
            self.error('--from must not be after --to')
        if result.end > completed_day(self.quant_config):
            self.error('--to must not be after the latest completed EOD date')
        return result
