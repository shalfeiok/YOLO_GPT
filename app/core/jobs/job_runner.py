from __future__ import annotations

import contextlib
import io
import random
import sys
import time
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from threading import Event, RLock, get_ident
from typing import Any, Generic, TypeVar, cast

from app.core.errors import CancelledError, InfrastructureError, IntegrationError
from app.core.events import EventBus
from app.core.events.job_events import (
    JobCancelled,
    JobFailed,
    JobFinished,
    JobLogLine,
    JobProgress,
    JobRetrying,
    JobStarted,
    JobTimedOut,
)

T = TypeVar("T")
LOG_BATCH_INTERVAL_SEC = 0.15
LOG_BATCH_MAX_LINES = 40


class _ThreadLocalTextRouter(io.TextIOBase):
    def __init__(self, fallback: io.TextIOBase) -> None:
        self._fallback = fallback
        self._targets: dict[int, io.TextIOBase] = {}
        self._lock = RLock()

    def bind_current(self, target: io.TextIOBase) -> int:
        tid = get_ident()
        with self._lock:
            self._targets[tid] = target
        return tid

    def unbind(self, tid: int) -> None:
        with self._lock:
            self._targets.pop(tid, None)

    def _target(self) -> io.TextIOBase:
        with self._lock:
            return self._targets.get(get_ident(), self._fallback)

    def write(self, s: str) -> int:
        return self._target().write(s)

    def flush(self) -> None:
        self._target().flush()


_STDOUT_ROUTER: _ThreadLocalTextRouter | None = None
_STDERR_ROUTER: _ThreadLocalTextRouter | None = None


def _ensure_stdio_routers() -> tuple[_ThreadLocalTextRouter, _ThreadLocalTextRouter]:
    global _STDOUT_ROUTER, _STDERR_ROUTER
    if _STDOUT_ROUTER is None:
        out = _ThreadLocalTextRouter(cast(io.TextIOBase, sys.stdout))
        sys.stdout = out
        _STDOUT_ROUTER = out
    if _STDERR_ROUTER is None:
        err = _ThreadLocalTextRouter(cast(io.TextIOBase, sys.stderr))
        sys.stderr = err
        _STDERR_ROUTER = err
    return _STDOUT_ROUTER, _STDERR_ROUTER


class CancelToken:
    """Cooperative cancellation token for background jobs."""

    def __init__(self) -> None:
        self._evt = Event()

    def cancel(self) -> None:
        self._evt.set()

    def is_cancelled(self) -> bool:
        return self._evt.is_set()


ProgressFn = Callable[[float, str | None], None]
JobFn = Callable[[CancelToken, ProgressFn], T]


@dataclass(slots=True)
class JobHandle(Generic[T]):
    job_id: str
    name: str
    future: Future[T]
    cancel_token: CancelToken

    def cancel(self) -> None:
        self.cancel_token.cancel()


class JobRunner:
    """ThreadPool job runner that publishes lifecycle events to an EventBus."""

    def __init__(self, event_bus: EventBus, max_workers: int = 4) -> None:
        self._bus = event_bus
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="job")
        self._stdout_router, self._stderr_router = _ensure_stdio_routers()

    def submit(
        self,
        name: str,
        fn: JobFn[T],
        *,
        retries: int = 0,
        retry_backoff_sec: float = 0.75,
        retry_jitter: float = 0.3,
        retry_deadline_sec: float | None = None,
        timeout_sec: float | None = None,
    ) -> JobHandle[T]:
        job_id = uuid.uuid4().hex
        token = CancelToken()

        def progress(p: float, msg: str | None = None) -> None:
            pp = 0.0 if p < 0 else 1.0 if p > 1 else p
            self._bus.publish(JobProgress(job_id=job_id, name=name, progress=pp, message=msg))

        def log_line(line: str) -> None:
            ln = line.rstrip("\n")
            if not ln:
                return
            self._bus.publish(JobLogLine(job_id=job_id, name=name, line=ln))

        pending_log_lines: list[str] = []
        last_log_flush_ts = 0.0

        def flush_logs(*, force: bool = False) -> None:
            nonlocal last_log_flush_ts
            if not pending_log_lines:
                return
            now = time.monotonic()
            if not force and (now - last_log_flush_ts) < LOG_BATCH_INTERVAL_SEC:
                return
            while pending_log_lines:
                chunk = pending_log_lines[:LOG_BATCH_MAX_LINES]
                del pending_log_lines[:LOG_BATCH_MAX_LINES]
                log_line("\n".join(chunk))
            last_log_flush_ts = now

        class _LineEmitter(io.TextIOBase):
            def __init__(self) -> None:
                self._buf = ""

            def write(self, s: str) -> int:
                self._buf += s
                while "\n" in self._buf:
                    line, self._buf = self._buf.split("\n", 1)
                    if line.strip():
                        pending_log_lines.append(line)
                    flush_logs()
                return len(s)

            def flush(self) -> None:
                if self._buf.strip():
                    pending_log_lines.append(self._buf)
                self._buf = ""
                flush_logs(force=True)

        self._bus.publish(JobStarted(job_id=job_id, name=name))
        progress(0.0, "started")

        def _run_once() -> T:
            if token.is_cancelled():
                raise CancelledError("Job cancelled")

            stdout = _LineEmitter()
            stderr = _LineEmitter()

            start_ts = time.monotonic()

            def _check_timeout() -> None:
                if timeout_sec is None:
                    return
                if (time.monotonic() - start_ts) > float(timeout_sec):
                    token.cancel()
                    self._bus.publish(
                        JobTimedOut(job_id=job_id, name=name, timeout_sec=float(timeout_sec))
                    )
                    raise TimeoutError(f"Job timed out after {timeout_sec}s")

            def _progress_with_timeout(p: float, msg: str | None = None) -> None:
                _check_timeout()
                progress(p, msg)

            stdout_tid = self._stdout_router.bind_current(stdout)
            stderr_tid = self._stderr_router.bind_current(stderr)
            try:
                _check_timeout()
                with contextlib.redirect_stdout(self._stdout_router), contextlib.redirect_stderr(
                    self._stderr_router
                ):
                    result = fn(token, _progress_with_timeout)
                _check_timeout()
                return result
            finally:
                stdout.flush()
                stderr.flush()
                self._stdout_router.unbind(stdout_tid)
                self._stderr_router.unbind(stderr_tid)

        def _run() -> T:
            max_attempts = max(1, retries + 1)
            start_t = time.monotonic()
            attempt = 0
            while True:
                attempt += 1
                try:
                    result = _run_once()
                    if token.is_cancelled():
                        raise CancelledError("Job cancelled")
                    progress(1.0, "finished")
                    self._bus.publish(JobFinished(job_id=job_id, name=name, result=result))
                    return result
                except CancelledError:
                    self._bus.publish(JobCancelled(job_id=job_id, name=name))
                    raise
                except TimeoutError:
                    # JobTimedOut already published in _run_once.
                    raise
                except Exception as e:  # noqa: BLE001
                    if token.is_cancelled():
                        self._bus.publish(JobCancelled(job_id=job_id, name=name))
                        raise CancelledError("Job cancelled") from e
                    # Retry only for integration/infrastructure failures.
                    is_retryable = isinstance(e, (IntegrationError, InfrastructureError))
                    if (
                        retry_deadline_sec is not None
                        and (time.monotonic() - start_t) >= retry_deadline_sec
                    ):
                        is_retryable = False

                    if is_retryable and attempt < max_attempts:
                        self._bus.publish(
                            JobRetrying(
                                job_id=job_id,
                                name=name,
                                attempt=attempt,
                                max_attempts=max_attempts,
                                error=str(e),
                            )
                        )
                        # Exponential backoff with jitter (bounded)
                        base = min(10.0, retry_backoff_sec * (1.6 ** (attempt - 1)))
                        j = 0.0 if retry_jitter <= 0 else min(0.9, float(retry_jitter))
                        sleep_s = base if j == 0 else base * (1.0 + random.uniform(-j, j))
                        if sleep_s < 0.0:
                            sleep_s = 0.0
                        progress(
                            max(0.0, min(0.95, (attempt - 1) / max_attempts)),
                            f"retrying in {sleep_s:.1f}s",
                        )
                        time.sleep(sleep_s)
                        continue
                    self._bus.publish(JobFailed(job_id=job_id, name=name, error=str(e)))
                    raise

        fut = self._pool.submit(_run)
        return JobHandle(job_id=job_id, name=name, future=fut, cancel_token=token)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
