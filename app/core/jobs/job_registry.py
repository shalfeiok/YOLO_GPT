from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
from threading import RLock
from typing import Any

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
from app.core.jobs.job_event_store import JobEventStore, pack_job_event


@dataclass(slots=True)
class JobRecord:
    job_id: str
    name: str
    status: str = "running"  # running|retrying|finished|failed|cancelled|timed_out
    progress: float = 0.0
    message: str | None = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    error: str | None = None
    logs: list[str] = field(default_factory=list)
    rerun: Callable[[], Any] | None = None
    cancel: Callable[[], None] | None = None


class JobRegistry:
    """Registry of background jobs (UI history, retry, logs).

    - Keeps in-memory state for fast UI rendering.
    - Optionally persists Job* events to a store and replays them on startup.
    """

    def __init__(
        self,
        event_bus: EventBus,
        *,
        max_log_lines: int = 400,
        max_jobs: int = 200,
        store: JobEventStore | None = None,
        replay_on_start: bool = True,
    ) -> None:
        self._bus = event_bus
        self._max_log_lines = max_log_lines
        self._max_jobs = max_jobs
        self._jobs: dict[str, JobRecord] = {}
        self._pending_rerun: dict[str, Callable[[], Any]] = {}
        self._pending_cancel: dict[str, Callable[[], None]] = {}
        self._store = store
        self._lock = RLock()

        # Subscribe to live events.
        self._bus.subscribe(JobStarted, self._on_started)
        self._bus.subscribe(JobProgress, self._on_progress)
        self._bus.subscribe(JobLogLine, self._on_log)
        self._bus.subscribe(JobFinished, self._on_finished)
        self._bus.subscribe(JobFailed, self._on_failed)
        self._bus.subscribe(JobCancelled, self._on_cancelled)
        self._bus.subscribe(JobRetrying, self._on_retrying)
        self._bus.subscribe(JobTimedOut, self._on_timed_out)

        # Replay persisted events (dev-friendly and useful after crashes).
        if self._store is not None and replay_on_start:
            self._replay_from_store()

    def set_rerun(self, job_id: str, rerun: Callable[[], Any]) -> None:
        if not job_id:
            return
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is not None:
                rec.rerun = rerun
            else:
                self._pending_rerun[job_id] = rerun
                self._purge_pending_if_needed()

    def set_cancel(self, job_id: str, cancel: Callable[[], None]) -> None:
        if not job_id:
            return
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is not None:
                rec.cancel = cancel
            else:
                self._pending_cancel[job_id] = cancel
                self._purge_pending_if_needed()

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            rec = self._jobs.get(job_id)
            return None if rec is None else self._copy_record(rec)

    def list(self) -> list[JobRecord]:
        with self._lock:
            records = sorted(self._jobs.values(), key=lambda r: r.started_at, reverse=True)
            return [self._copy_record(r) for r in records]

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()
            self._pending_rerun.clear()
            self._pending_cancel.clear()
        if self._store is not None:
            self._store.clear()

    def _copy_record(self, rec: JobRecord) -> JobRecord:
        return replace(rec, logs=list(rec.logs))

    def _purge_pending_if_needed(self) -> None:
        if self._max_jobs <= 0:
            return
        overflow = len(self._pending_rerun) - self._max_jobs
        if overflow > 0:
            for key in list(self._pending_rerun.keys())[:overflow]:
                self._pending_rerun.pop(key, None)
        overflow = len(self._pending_cancel) - self._max_jobs
        if overflow > 0:
            for key in list(self._pending_cancel.keys())[:overflow]:
                self._pending_cancel.pop(key, None)

    def _purge_if_needed(self) -> None:
        """Keep only the newest N jobs to avoid unbounded memory growth."""
        if self._max_jobs <= 0:
            return
        if len(self._jobs) <= self._max_jobs:
            return
        # Purge oldest by started_at.
        oldest = sorted(self._jobs.values(), key=lambda r: r.started_at)[
            : len(self._jobs) - self._max_jobs
        ]
        for rec in oldest:
            self._jobs.pop(rec.job_id, None)

    def _persist(self, e: Any) -> None:
        if self._store is None:
            return
        try:
            self._store.append(pack_job_event(e))
        except Exception:
            # Never crash the app because persistence failed.
            return

    def _replay_from_store(self) -> None:
        assert self._store is not None
        for rec in self._store.load():
            t = rec.get("type")
            data = rec.get("data") or {}
            if not isinstance(data, dict) or not isinstance(t, str):
                continue
            # Replay only what JobRegistry needs (ignore result payload).
            job_id = str(data.get("job_id", ""))
            name = str(data.get("name", ""))
            if not job_id or not name:
                continue

            if t == "JobStarted":
                self._apply_started(JobStarted(job_id=job_id, name=name), persist=False)
            elif t == "JobProgress":
                try:
                    progress = float(data.get("progress", 0.0))
                except Exception:
                    progress = 0.0
                msg = data.get("message")
                self._apply_progress(
                    JobProgress(job_id=job_id, name=name, progress=progress, message=msg),
                    persist=False,
                )
            elif t == "JobLogLine":
                line = str(data.get("line", ""))
                if line:
                    self._apply_log(JobLogLine(job_id=job_id, name=name, line=line), persist=False)
            elif t == "JobFinished":
                self._apply_finished(
                    JobFinished(job_id=job_id, name=name, result=None), persist=False
                )
            elif t == "JobFailed":
                err = str(data.get("error", ""))
                self._apply_failed(JobFailed(job_id=job_id, name=name, error=err), persist=False)
            elif t == "JobCancelled":
                self._apply_cancelled(JobCancelled(job_id=job_id, name=name), persist=False)
            elif t == "JobRetrying":
                try:
                    attempt = int(data.get("attempt", 1))
                    max_attempts = int(data.get("max_attempts", attempt))
                except Exception:
                    attempt, max_attempts = 1, 1
                err = str(data.get("error", ""))
                self._apply_retrying(
                    JobRetrying(
                        job_id=job_id,
                        name=name,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        error=err,
                    ),
                    persist=False,
                )
            elif t == "JobTimedOut":
                try:
                    timeout_sec = float(data.get("timeout_sec", 0.0))
                except Exception:
                    timeout_sec = 0.0
                self._apply_timed_out(
                    JobTimedOut(job_id=job_id, name=name, timeout_sec=timeout_sec), persist=False
                )

        with self._lock:
            self._purge_if_needed()

    # Event handlers
    def _ensure(self, job_id: str, name: str) -> JobRecord:
        rec = self._jobs.get(job_id)
        if rec is None:
            rec = JobRecord(job_id=job_id, name=name)
            self._jobs[job_id] = rec
        return rec

    def _apply_started(self, e: JobStarted, *, persist: bool) -> None:
        with self._lock:
            rec = self._jobs.get(e.job_id)
            if rec is None:
                rec = JobRecord(job_id=e.job_id, name=e.name)
                rec.rerun = self._pending_rerun.pop(e.job_id, None)
                rec.cancel = self._pending_cancel.pop(e.job_id, None)
                self._jobs[e.job_id] = rec
                self._purge_if_needed()
            else:
                # Idempotency: repeated JobStarted must not reset accumulated progress/logs/state.
                rec.name = e.name
                if rec.rerun is None:
                    rec.rerun = self._pending_rerun.pop(e.job_id, None)
                if rec.cancel is None:
                    rec.cancel = self._pending_cancel.pop(e.job_id, None)
        if persist:
            self._persist(e)

    def _apply_progress(self, e: JobProgress, *, persist: bool) -> None:
        with self._lock:
            rec = self._ensure(e.job_id, e.name)
            rec.progress = e.progress
            rec.message = e.message
        if persist:
            self._persist(e)

    def _apply_log(self, e: JobLogLine, *, persist: bool) -> None:
        with self._lock:
            rec = self._ensure(e.job_id, e.name)
            rec.logs.append(e.line)
            if len(rec.logs) > self._max_log_lines:
                rec.logs = rec.logs[-self._max_log_lines :]
        if persist:
            self._persist(e)

    def _apply_finished(self, e: JobFinished, *, persist: bool) -> None:
        with self._lock:
            rec = self._ensure(e.job_id, e.name)
            rec.status = "finished"
            rec.progress = 1.0
            rec.finished_at = datetime.utcnow()
        if persist:
            self._persist(e)

    def _apply_failed(self, e: JobFailed, *, persist: bool) -> None:
        with self._lock:
            rec = self._ensure(e.job_id, e.name)
            rec.status = "failed"
            rec.error = e.error
            rec.finished_at = datetime.utcnow()
        if persist:
            self._persist(e)

    def _apply_retrying(self, e: JobRetrying, *, persist: bool) -> None:
        with self._lock:
            rec = self._ensure(e.job_id, e.name)
            rec.status = "retrying"
            rec.message = f"retry {e.attempt}/{e.max_attempts}: {e.error}"
        if persist:
            self._persist(e)

    def _apply_timed_out(self, e: JobTimedOut, *, persist: bool) -> None:
        with self._lock:
            rec = self._ensure(e.job_id, e.name)
            rec.status = "timed_out"
            rec.error = f"timeout after {e.timeout_sec:.1f}s"
            rec.finished_at = datetime.utcnow()
        if persist:
            self._persist(e)

    def _apply_cancelled(self, e: JobCancelled, *, persist: bool) -> None:
        with self._lock:
            rec = self._ensure(e.job_id, e.name)
            rec.status = "cancelled"
            rec.finished_at = datetime.utcnow()
        if persist:
            self._persist(e)

    def _on_started(self, e: JobStarted) -> None:
        self._apply_started(e, persist=True)

    def _on_progress(self, e: JobProgress) -> None:
        self._apply_progress(e, persist=True)

    def _on_log(self, e: JobLogLine) -> None:
        self._apply_log(e, persist=True)

    def _on_finished(self, e: JobFinished) -> None:
        self._apply_finished(e, persist=True)

    def _on_failed(self, e: JobFailed) -> None:
        self._apply_failed(e, persist=True)

    def _on_retrying(self, e: JobRetrying) -> None:
        self._apply_retrying(e, persist=True)

    def _on_timed_out(self, e: JobTimedOut) -> None:
        self._apply_timed_out(e, persist=True)

    def _on_cancelled(self, e: JobCancelled) -> None:
        self._apply_cancelled(e, persist=True)
