"""Process-based job runner.

Why this exists:
- Threads cannot be force-killed safely.
- Some heavy ML/integration tasks can hang in native code or blocking I/O.

This runner executes a job in a separate process so we can enforce a hard timeout
by terminating the process. It uses a multiprocessing Queue to stream progress
and log lines back to the parent, which then publishes them via EventBus.

Notes:
- The submitted function MUST be picklable (top-level function, no closures).
- Cancellation is cooperative via a multiprocessing.Event, but timeout is hard.
"""

from __future__ import annotations

import contextlib
import io
import queue
import random
import time
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from multiprocessing import Queue, get_context
from multiprocessing.synchronize import Event as MpEvent
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


class ProcessCancelToken:
    def __init__(self, evt: MpEvent) -> None:
        self._evt = evt

    def cancel(self) -> None:
        self._evt.set()

    def is_cancelled(self) -> bool:
        return self._evt.is_set()


ProgressFn = Callable[[float, str | None], None]
JobFn = Callable[[ProcessCancelToken, ProgressFn], T]


@dataclass(slots=True)
class ProcessJobHandle(Generic[T]):
    job_id: str
    name: str
    future: Future[T]
    cancel_evt: MpEvent

    def cancel(self) -> None:
        self.cancel_evt.set()


def _child_entry(
    fn: Callable[[MpEvent, Callable[[float, str | None], None]], Any],
    cancel_evt: MpEvent,
    q: Queue,
) -> None:
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


def _close_ipc_queue(q: Queue) -> None:
    close = getattr(q, "close", None)
    if callable(close):
        close()
    join_thread = getattr(q, "join_thread", None)
    if callable(join_thread):
        join_thread()


class ProcessJobRunner:
    """Runs picklable jobs in a separate process."""

    def __init__(self, event_bus: EventBus, max_workers: int = 2) -> None:
        self._bus = event_bus
        # A small thread pool to supervise processes (start/join/terminate) without blocking UI.
        self._supervisor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="job-proc")
        self._ctx = get_context("spawn")

    def submit(
        self,
        name: str,
        fn: Callable[[MpEvent, Callable[[float, str | None], None]], T],
        *,
        retries: int = 0,
        retry_backoff_sec: float = 0.75,
        retry_jitter: float = 0.3,
        retry_deadline_sec: float | None = None,
        timeout_sec: float | None = None,
    ) -> ProcessJobHandle[T]:
        job_id = uuid.uuid4().hex
        cancel_evt: MpEvent = self._ctx.Event()
        self._bus.publish(JobStarted(job_id=job_id, name=name))
        self._bus.publish(JobProgress(job_id=job_id, name=name, progress=0.0, message="started"))

        def _run_attempt() -> T:
            if cancel_evt.is_set():
                self._bus.publish(JobCancelled(job_id=job_id, name=name))
                raise CancelledError("Job cancelled")

            q: Queue = self._ctx.Queue()
            p = self._ctx.Process(target=_child_entry, args=(cast(Any, fn), cancel_evt, q), daemon=True)
            p.start()

            started = time.monotonic()
            result: T | None = None
            error: str | None = None
            got_result = False

            # Queue feeder threads in multiprocessing can flush messages shortly after
            # the child process is already reported as dead. Keep polling briefly to avoid
            # dropping a terminal payload that was already produced by the child.
            drain_deadline: float | None = None

            try:
                while True:
                    if timeout_sec is not None and (time.monotonic() - started) > timeout_sec:
                        cancel_evt.set()
                        if p.is_alive():
                            p.terminate()
                        p.join(timeout=1.0)
                        self._bus.publish(JobTimedOut(job_id=job_id, name=name, timeout_sec=float(timeout_sec)))
                        raise TimeoutError(f"Job timed out after {timeout_sec}s")

                    if cancel_evt.is_set() and p.is_alive():
                        # Cooperative cancel first; then hard terminate.
                        p.terminate()
                        p.join(timeout=1.0)
                        self._bus.publish(JobCancelled(job_id=job_id, name=name))
                        raise CancelledError("Job cancelled")

                    alive = p.is_alive()
                    if not alive and drain_deadline is None:
                        drain_deadline = time.monotonic() + 0.3

                    get_timeout = 0.15 if alive else 0.03
                    try:
                        msg = q.get(timeout=get_timeout)
                    except queue.Empty:
                        if alive:
                            continue
                        if drain_deadline is not None and time.monotonic() < drain_deadline:
                            continue
                        break

                    kind = msg[0]
                    if kind == "progress":
                        _, prog, m = msg
                        self._bus.publish(
                            JobProgress(job_id=job_id, name=name, progress=float(prog), message=cast(str | None, m))
                        )
                    elif kind == "log":
                        _, line = msg
                        ln = cast(str, line).rstrip("\n")
                        if ln.strip():
                            self._bus.publish(JobLogLine(job_id=job_id, name=name, line=ln))
                    elif kind == "result":
                        _, res = msg
                        result = cast(T, res)
                        got_result = True
                        break
                    elif kind == "error":
                        _, err = msg
                        error = cast(str, err)
                        break
                    elif kind == "cancelled":
                        # Child cooperatively cancelled.
                        self._bus.publish(JobCancelled(job_id=job_id, name=name))
                        raise CancelledError("Job cancelled")
                    else:
                        error = f"Unknown child message kind: {kind!r}"
                        break
            finally:
                p.join(timeout=0.5)
                if p.is_alive():
                    p.terminate()
                    p.join(timeout=0.5)
                with contextlib.suppress(Exception):
                    _close_ipc_queue(q)

            if cancel_evt.is_set():
                self._bus.publish(JobCancelled(job_id=job_id, name=name))
                raise CancelledError("Job cancelled")
            if error is not None:
                raise RuntimeError(error)
            if not got_result:
                exitcode = getattr(p, "exitcode", None)
                if isinstance(exitcode, int) and exitcode != 0:
                    raise RuntimeError(f"Job process exited with code {exitcode} without a result payload")
                raise RuntimeError("Job process exited without a result payload")
            return cast(T, result)

        def _run() -> T:
            max_attempts = max(1, retries + 1)
            start_t = time.monotonic()
            attempt = 0
            while True:
                attempt += 1
                try:
                    res = _run_attempt()
                    self._bus.publish(JobProgress(job_id=job_id, name=name, progress=1.0, message="finished"))
                    self._bus.publish(JobFinished(job_id=job_id, name=name, result=res))
                    return res
                except CancelledError:
                    raise
                except TimeoutError:
                    raise
                except Exception as e:  # noqa: BLE001
                    is_retryable = isinstance(e, (IntegrationError, InfrastructureError))
                    if retry_deadline_sec is not None and (time.monotonic() - start_t) >= retry_deadline_sec:
                        is_retryable = False

                    if is_retryable and attempt < max_attempts and not cancel_evt.is_set():
                        self._bus.publish(
                            JobRetrying(
                                job_id=job_id,
                                name=name,
                                attempt=attempt,
                                max_attempts=max_attempts,
                                error=str(e),
                            )
                        )
                        base = min(10.0, retry_backoff_sec * (1.6 ** (attempt - 1)))
                        j = 0.0 if retry_jitter <= 0 else min(0.9, float(retry_jitter))
                        sleep_s = base if j == 0 else base * (1.0 + random.uniform(-j, j))
                        if sleep_s < 0.0:
                            sleep_s = 0.0
                        self._bus.publish(
                            JobProgress(
                                job_id=job_id,
                                name=name,
                                progress=max(0.0, min(0.95, (attempt - 1) / max_attempts)),
                                message=f"retrying in {sleep_s:.1f}s",
                            )
                        )
                        time.sleep(sleep_s)
                        continue
                    self._bus.publish(JobFailed(job_id=job_id, name=name, error=str(e)))
                    raise

        fut = self._supervisor.submit(_run)
        return ProcessJobHandle(job_id=job_id, name=name, future=fut, cancel_evt=cancel_evt)
