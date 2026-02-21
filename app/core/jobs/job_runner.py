from __future__ import annotations

import contextlib
import io
import random
import time
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from threading import Event, Thread
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

        class _LineEmitter(io.TextIOBase):
            def __init__(self) -> None:
                self._buf = ""

            def write(self, s: str) -> int:
                self._buf += s
                while "\n" in self._buf:
                    line, self._buf = self._buf.split("\n", 1)
                    log_line(line)
                return len(s)

            def flush(self) -> None:
                if self._buf.strip():
                    log_line(self._buf)
                self._buf = ""

        self._bus.publish(JobStarted(job_id=job_id, name=name))
        progress(0.0, "started")

        def _run_once() -> T:
            if token.is_cancelled():
                raise CancelledError("Job cancelled")

            stdout = _LineEmitter()
            stderr = _LineEmitter()

            # Fast path: no timeout requested => run directly in this worker thread.
            if timeout_sec is None:
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    result = fn(token, progress)
                stdout.flush()
                stderr.flush()
                return result

            # Best-effort timeout: run fn in an inner thread so we can join with a deadline.
            result_box: dict[str, Any] = {}
            err_box: dict[str, BaseException] = {}

            def _inner() -> None:
                try:
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        result_box["result"] = fn(token, progress)
                except BaseException as e:  # noqa: BLE001
                    err_box["error"] = e

            t = Thread(target=_inner, name=f"job-inner-{job_id[:8]}", daemon=True)
            t.start()
            t.join(timeout=timeout_sec)
            if t.is_alive():
                # Cooperative timeout: ask the job to stop; if it doesn't, the inner thread may keep running.
                token.cancel()
                self._bus.publish(JobTimedOut(job_id=job_id, name=name, timeout_sec=float(timeout_sec)))
                raise TimeoutError(f"Job timed out after {timeout_sec}s")

            stdout.flush()
            stderr.flush()
            if "error" in err_box:
                raise err_box["error"]
            if "result" not in result_box:
                raise RuntimeError("Job finished without result")
            return cast(T, result_box["result"])

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
                    if retry_deadline_sec is not None and (time.monotonic() - start_t) >= retry_deadline_sec:
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
                        progress(max(0.0, min(0.95, (attempt - 1) / max_attempts)), f"retrying in {sleep_s:.1f}s")
                        time.sleep(sleep_s)
                        continue
                    self._bus.publish(JobFailed(job_id=job_id, name=name, error=str(e)))
                    raise

        fut = self._pool.submit(_run)
        return JobHandle(job_id=job_id, name=name, future=fut, cancel_token=token)
