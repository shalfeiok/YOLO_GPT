from __future__ import annotations

import re
import time

from app.console_redirect import strip_ansi
from app.core.events import EventBus
from app.core.events.job_events import JobLogLine

LOG_BATCH_INTERVAL_SEC = 0.15
LOG_BATCH_MAX_LINES = 40
_CTRL_RE = re.compile(r"[\x00-\x08\x0B-\x1F\x7F-\x9F]")


def _clean_log_line(line: str) -> str:
    return _CTRL_RE.sub("", strip_ansi(str(line))).strip()


class JobLogBuffer:
    def __init__(self, bus: EventBus, job_id: str, name: str) -> None:
        self._bus = bus
        self._job_id = job_id
        self._name = name
        self._pending: list[str] = []
        self._last_flush_ts = 0.0

    def add_line(self, line: str) -> None:
        ln = _clean_log_line(line)
        if ln:
            self._pending.append(ln)
            self.flush()

    def flush(self, *, force: bool = False) -> None:
        if not self._pending:
            return
        now = time.monotonic()
        if not force and (now - self._last_flush_ts) < LOG_BATCH_INTERVAL_SEC:
            return
        while self._pending:
            chunk = self._pending[:LOG_BATCH_MAX_LINES]
            del self._pending[:LOG_BATCH_MAX_LINES]
            self._bus.publish(
                JobLogLine(job_id=self._job_id, name=self._name, line="\n".join(chunk))
            )
        self._last_flush_ts = now
