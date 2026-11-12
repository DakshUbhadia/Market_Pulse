"""Small durable progress ledger. A later success never hides an earlier hole."""
import json
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from quant.data.http import atomic_write


@contextmanager
def state_lock(path):
    """OS locks are released on process exit, including a missed/crashed job."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            stream.seek(0)
            if not stream.read(1):
                stream.write(b'0')
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


class PipelineState:
    def __init__(self, config):
        self.config = config
        self.path = config.data_dir / 'state' / 'pipeline_state.json'
        self.data = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {}

    def record(self, source, *, status, day=None, error=None, **details):
        with state_lock(self.path.with_suffix('.lock')):
            self._record(source, status=status, day=day, error=error, **details)

    def _record(self, source, *, status, day=None, error=None, **details):
        # Other pipeline stages may have written since this instance was created.
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding='utf-8'))
        row = self.data.setdefault(source, {})
        now = datetime.now(ZoneInfo(self.config.timezone)).isoformat()
        row.update(status=status, last_checked_at=now, **details)
        if status == 'READY':
            row['last_successful_at'] = now
            if day is not None:
                row['last_success'] = max(row.get('last_success', str(day)), str(day))
            row.pop('error', None)
        elif error:
            row['error'] = str(error)
        atomic_write(self.path, json.dumps(self.data, indent=2).encode())

    def overlap_start(self, source, initial, end, days=14):
        # Resume from the last *successful* poll, not the last attempted poll.
        row = self.data.get(source, {})
        last = row.get('checked_through')
        if not last or str(initial) < row.get('checked_from', str(initial)):
            return initial
        from datetime import date
        return max(initial, min(end, date.fromisoformat(last)) - timedelta(days=days))
