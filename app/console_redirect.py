"""Console capture for in-app training log: logging handler (preferred) or stdout redirect (legacy)."""

from __future__ import annotations

import logging
import re
import sys
import threading
from queue import Queue

# Убираем ANSI-последовательности (например \x1b[K — erase to end of line), чтобы в консоли не было мусора
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\[?[0-9;]*[a-zA-Z]?")

# Global lock/stack to make stdout/stderr redirect thread-safe and re-entrant.
_STREAM_LOCK = threading.RLock()
_REDIRECT_STACK: list[tuple[object, object]] = []


def strip_ansi(text: str) -> str:
    """Удаляет ANSI escape-последовательности из строки."""
    return _ANSI_ESCAPE_RE.sub("", text)


class QueueWriter:
    """Writes to a queue (each write is one put); original stream can be preserved."""

    def __init__(self, queue: Queue, original: object | None = None) -> None:
        self._queue = queue
        self._original = original
        self._buffer: list[str] = []

    def write(self, data: str) -> None:
        if not isinstance(data, str):
            data = str(data)
        if self._original is not None and hasattr(self._original, "write"):
            self._original.write(data)
        # buffer and put by lines so UI gets full lines
        for c in data:
            if c == "\r":
                continue
            if c == "\n":
                line = strip_ansi("".join(self._buffer))
                self._buffer.clear()
                if line:
                    self._queue.put(line)
            else:
                self._buffer.append(c)
        if self._buffer and (data.endswith("\n") or len(data) > 0):
            # no newline at end - put rest on flush or next write
            pass

    def flush(self) -> None:
        if self._buffer:
            line = strip_ansi("".join(self._buffer))
            self._buffer.clear()
            if line:
                self._queue.put(line)
        if self._original is not None and hasattr(self._original, "flush"):
            self._original.flush()


def redirect_stdout_stderr_to_queue(
    queue: Queue, also_keep_original: bool = False
) -> tuple[object, object]:
    """Replace sys.stdout and sys.stderr with QueueWriter. Returns (old_stdout, old_stderr).

    Thread-safe and re-entrant:
    - Multiple nested redirects are supported (LIFO restore).
    - A global lock prevents concurrent mutation of sys.stdout/sys.stderr across threads.
    """
    with _STREAM_LOCK:
        old_out, old_err = sys.stdout, sys.stderr
        _REDIRECT_STACK.append((old_out, old_err))

        orig_out = old_out if also_keep_original else None
        orig_err = old_err if also_keep_original else None
        sys.stdout = QueueWriter(queue, orig_out)
        sys.stderr = QueueWriter(queue, orig_err)
        return old_out, old_err


def restore_stdout_stderr(old_stdout: object, old_stderr: object) -> None:
    """Restore previous sys.stdout and sys.stderr.

    Safe with nesting: restores only the most recent redirect by default.
    If restore order is violated, attempts best-effort recovery and logs at debug level.
    """
    with _STREAM_LOCK:
        if _REDIRECT_STACK:
            top_out, top_err = _REDIRECT_STACK[-1]
            if top_out is old_stdout and top_err is old_stderr:
                _REDIRECT_STACK.pop()
            else:
                # Restore called out-of-order: remove first matching entry (best effort).
                idx = None
                for i in range(len(_REDIRECT_STACK) - 1, -1, -1):
                    if _REDIRECT_STACK[i][0] is old_stdout and _REDIRECT_STACK[i][1] is old_stderr:
                        idx = i
                        break
                if idx is not None:
                    _REDIRECT_STACK.pop(idx)
                    logging.getLogger(__name__).debug(
                        "stdout/stderr restore called out-of-order; recovered via stack removal"
                    )
                else:
                    logging.getLogger(__name__).debug(
                        "stdout/stderr restore called with unknown streams; restoring anyway"
                    )
        sys.stdout = old_stdout
        sys.stderr = old_stderr


class TrainingLogHandler(logging.Handler):
    """
    Logging handler that pushes log records to a queue for the in-app console.
    Use this instead of redirecting sys.stdout (Part 3.8): no global stream mutation.
    """

    def __init__(self, queue: Queue) -> None:
        super().__init__()
        self._queue = queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            if msg:
                self._queue.put(strip_ansi(msg))
        except Exception:
            self.handleError(record)


def attach_training_log_handler(queue: Queue) -> list[tuple[logging.Logger, TrainingLogHandler]]:
    """
    Attach TrainingLogHandler to root and ultralytics loggers. Returns list of
    (logger, handler) so caller can remove them in finally.
    """
    handler = TrainingLogHandler(queue)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(message)s"))
    attached: list[tuple[logging.Logger, TrainingLogHandler]] = []
    for name in ("", "ultralytics"):
        logger = logging.getLogger(name) if name else logging.getLogger()
        logger.addHandler(handler)
        attached.append((logger, handler))
    return attached


def detach_training_log_handler(attached: list[tuple[logging.Logger, TrainingLogHandler]]) -> None:
    """Remove handlers added by attach_training_log_handler."""
    for logger, handler in attached:
        try:
            logger.removeHandler(handler)
        except Exception:
            import logging

            logging.getLogger(__name__).debug("Failed to detach logging handler", exc_info=True)
