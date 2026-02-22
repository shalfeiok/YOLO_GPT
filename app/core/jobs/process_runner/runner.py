from __future__ import annotations

import contextlib
import math
import queue
import random
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Queue, get_context
from multiprocessing.synchronize import Event as MpEvent
from typing import Any, TypeVar, cast

from app.core.errors import CancelledError, InfrastructureError, IntegrationError
from app.core.events import EventBus
from app.core.events.job_events import (
    JobCancelled,
    JobFailed,
    JobFinished,
    JobProgress,
    JobRetrying,
    JobStarted,
    JobTimedOut,
)

from .child_worker import child_entry, close_ipc_queue
from .log_buffer import JobLogBuffer
from .types import ProcessJobHandle

T = TypeVar("T")


class ProcessJobRunner:
    """Runs picklable jobs in a separate process."""

    def __init__(self, event_bus: EventBus, max_workers: int = 2) -> None:
        self._bus = event_bus
        self._supervisor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="job-proc"
        )
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
            p = self._ctx.Process(
                target=child_entry, args=(cast(Any, fn), cancel_evt, q), daemon=True
            )
            process_started = False
            started = time.monotonic()
            result: T | None = None
            error: str | None = None
            got_result = False
            logs = JobLogBuffer(self._bus, job_id, name)
            drain_deadline: float | None = None
            alive = False
            try:
                p.start()
                process_started = True
                while True:
                    if timeout_sec is not None and (time.monotonic() - started) > timeout_sec:
                        cancel_evt.set()
                        if p.is_alive():
                            p.terminate()
                        p.join(timeout=1.0)
                        self._bus.publish(
                            JobTimedOut(job_id=job_id, name=name, timeout_sec=float(timeout_sec))
                        )
                        raise TimeoutError(f"Job timed out after {timeout_sec}s")

                    if cancel_evt.is_set() and p.is_alive():
                        p.terminate()
                        p.join(timeout=1.0)
                        self._bus.publish(JobCancelled(job_id=job_id, name=name))
                        raise CancelledError("Job cancelled")

                    alive = p.is_alive()
                    if not alive and drain_deadline is None:
                        drain_deadline = time.monotonic() + 0.3

                    try:
                        msg = q.get(timeout=0.15 if alive else 0.03)
                    except queue.Empty:
                        if alive or (
                            drain_deadline is not None and time.monotonic() < drain_deadline
                        ):
                            continue
                        break

                    error = self._process_message(msg, job_id, name, logs)
                    if error is None:
                        if isinstance(msg, tuple) and len(msg) == 2 and msg[0] == "result":
                            result = cast(T, msg[1])
                            got_result = True
                            break
                        continue
                    if error == "cancelled":
                        logs.flush(force=True)
                        raise CancelledError("Job cancelled")
                    logs.flush(force=True)
                    break

                logs.flush(force=not alive)
            finally:
                if process_started:
                    p.join(timeout=0.5)
                    if p.is_alive():
                        p.terminate()
                        p.join(timeout=0.5)
                with contextlib.suppress(Exception):
                    close_ipc_queue(q)

            if cancel_evt.is_set():
                self._bus.publish(JobCancelled(job_id=job_id, name=name))
                raise CancelledError("Job cancelled")
            logs.flush(force=True)
            if error is not None:
                raise RuntimeError(error)
            if not got_result:
                exitcode = getattr(p, "exitcode", None)
                if isinstance(exitcode, int) and exitcode != 0:
                    raise RuntimeError(
                        f"Job process exited with code {exitcode} without a result payload"
                    )
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
                    self._bus.publish(
                        JobProgress(job_id=job_id, name=name, progress=1.0, message="finished")
                    )
                    self._bus.publish(JobFinished(job_id=job_id, name=name, result=res))
                    return res
                except (CancelledError, TimeoutError):
                    raise
                except Exception as e:  # noqa: BLE001
                    is_retryable = isinstance(e, (IntegrationError, InfrastructureError))
                    if (
                        retry_deadline_sec is not None
                        and (time.monotonic() - start_t) >= retry_deadline_sec
                    ):
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
                        self._bus.publish(
                            JobProgress(
                                job_id=job_id,
                                name=name,
                                progress=max(0.0, min(0.95, (attempt - 1) / max_attempts)),
                                message=f"retrying in {max(0.0, sleep_s):.1f}s",
                            )
                        )
                        time.sleep(max(0.0, sleep_s))
                        continue
                    self._bus.publish(JobFailed(job_id=job_id, name=name, error=str(e)))
                    raise

        fut = self._supervisor.submit(_run)
        return ProcessJobHandle(job_id=job_id, name=name, future=fut, cancel_evt=cancel_evt)

    def _process_message(self, msg: Any, job_id: str, name: str, logs: JobLogBuffer) -> str | None:
        if not isinstance(msg, tuple) or len(msg) == 0:
            return f"Malformed child message: {msg!r}"
        kind = msg[0]
        if not isinstance(kind, str):
            return f"Malformed child message kind: {kind!r}"
        if kind == "progress":
            if len(msg) != 3:
                return f"Malformed child progress message: {msg!r}"
            _, prog, message = msg
            try:
                raw_progress = float(prog)
            except (TypeError, ValueError):
                return f"Malformed child progress payload: {msg!r}"
            if not math.isfinite(raw_progress):
                return f"Malformed child progress payload: {msg!r}"
            prog_val = 0.0 if raw_progress < 0 else 1.0 if raw_progress > 1 else raw_progress
            self._bus.publish(
                JobProgress(
                    job_id=job_id,
                    name=name,
                    progress=prog_val,
                    message=None if message is None else str(message),
                )
            )
            return None
        if kind == "log":
            if len(msg) != 2:
                return f"Malformed child log message: {msg!r}"
            logs.add_line(str(msg[1]))
            return None
        if kind == "result":
            return None if len(msg) == 2 else f"Malformed child result message: {msg!r}"
        if kind == "error":
            return str(msg[1]) if len(msg) == 2 else f"Malformed child error message: {msg!r}"
        if kind == "cancelled":
            if len(msg) != 2:
                return f"Malformed child cancelled message: {msg!r}"
            self._bus.publish(JobCancelled(job_id=job_id, name=name))
            return "cancelled"
        return f"Unknown child message kind: {kind!r}"
