from __future__ import annotations

import contextlib
import io
from multiprocessing import Queue
from multiprocessing.synchronize import Event as MpEvent
from typing import Any

from app.core.errors import CancelledError


def child_entry(fn: Any, cancel_evt: MpEvent, q: Queue) -> None:
    def progress(p: float, msg: str | None = None) -> None:
        pp = 0.0 if p < 0 else 1.0 if p > 1 else p
        q.put(("progress", pp, msg))

    class _LineEmitter(io.TextIOBase):
        def __init__(self) -> None:
            self._buf = ""

        def write(self, s: str) -> int:
            self._buf += s
            while "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
                if line.strip():
                    q.put(("log", line))
            return len(s)

        def flush(self) -> None:
            if self._buf.strip():
                q.put(("log", self._buf))
            self._buf = ""

    stdout = _LineEmitter()
    stderr = _LineEmitter()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            res = fn(cancel_evt, progress)
        stdout.flush()
        stderr.flush()
        q.put(("result", res))
    except CancelledError as e:
        stdout.flush()
        stderr.flush()
        q.put(("cancelled", str(e)))
    except BaseException as e:  # noqa: BLE001
        stdout.flush()
        stderr.flush()
        q.put(("error", repr(e)))


def close_ipc_queue(q: Queue) -> None:
    close = getattr(q, "close", None)
    if callable(close):
        close()
    join_thread = getattr(q, "join_thread", None)
    if callable(join_thread):
        join_thread()
