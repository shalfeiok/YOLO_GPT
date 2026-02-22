from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
from threading import RLock
from typing import Any

from app.core.events import EventBus
from app.core.events.event_bus import Subscription
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
from app.core.jobs.job_registry_replay import replay_records


@dataclass(slots=True)
class JobRecord:
    job_id: str
    name: str
    status: str = "running"
    progress: float = 0.0
    message: str | None = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    error: str | None = None
    logs: list[str] = field(default_factory=list)
    rerun: Callable[[], Any] | None = None
    cancel: Callable[[], None] | None = None


class JobRegistry:
    """Registry of background jobs (UI history, retry, logs)."""

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
        self._subscriptions: list[Subscription] = []
        self._subscribe_handlers()
        if self._store is not None and replay_on_start:
            replay_records(self)

    def _subscribe_handlers(self) -> None:
        self._subscriptions.extend(
            [
                self._bus.subscribe(JobStarted, self._on_started),
                self._bus.subscribe(JobProgress, self._on_progress),
                self._bus.subscribe(JobLogLine, self._on_log),
                self._bus.subscribe(JobFinished, self._on_finished),
                self._bus.subscribe(JobFailed, self._on_failed),
                self._bus.subscribe(JobCancelled, self._on_cancelled),
                self._bus.subscribe(JobRetrying, self._on_retrying),
                self._bus.subscribe(JobTimedOut, self._on_timed_out),
            ]
        )

    def close(self) -> None:
        for sub in self._subscriptions:
            self._bus.unsubscribe(sub)
        self._subscriptions.clear()

    def set_rerun(self, job_id: str, rerun: Callable[[], Any]) -> None:
        self._set_pending_action(job_id, rerun, self._pending_rerun, "rerun")

    def set_cancel(self, job_id: str, cancel: Callable[[], None]) -> None:
        self._set_pending_action(job_id, cancel, self._pending_cancel, "cancel")

    def _set_pending_action(
        self, job_id: str, action: Any, pending: dict[str, Any], field_name: str
    ) -> None:
        if not job_id:
            return
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is not None:
                setattr(rec, field_name, action)
            else:
                pending[job_id] = action
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
        for pending in (self._pending_rerun, self._pending_cancel):
            overflow = len(pending) - self._max_jobs
            if overflow > 0:
                for key in list(pending.keys())[:overflow]:
                    pending.pop(key, None)

    def _purge_if_needed(self) -> None:
        if self._max_jobs <= 0 or len(self._jobs) <= self._max_jobs:
            return
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
            return

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
                rec.name = e.name
                rec.rerun = rec.rerun or self._pending_rerun.pop(e.job_id, None)
                rec.cancel = rec.cancel or self._pending_cancel.pop(e.job_id, None)
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
            parts = [part for part in str(e.line).splitlines() if part.strip()]
            if not parts:
                return
            rec.logs.extend(parts)
            if len(rec.logs) > self._max_log_lines:
                rec.logs = rec.logs[-self._max_log_lines :]
        if persist:
            self._persist(e)

    def _apply_finished(self, e: JobFinished, *, persist: bool) -> None:
        self._set_terminal(e.job_id, e.name, "finished", None, persist, e)

    def _apply_failed(self, e: JobFailed, *, persist: bool) -> None:
        self._set_terminal(e.job_id, e.name, "failed", e.error, persist, e)

    def _apply_retrying(self, e: JobRetrying, *, persist: bool) -> None:
        with self._lock:
            rec = self._ensure(e.job_id, e.name)
            rec.status = "retrying"
            rec.message = f"retry {e.attempt}/{e.max_attempts}: {e.error}"
        if persist:
            self._persist(e)

    def _apply_timed_out(self, e: JobTimedOut, *, persist: bool) -> None:
        self._set_terminal(
            e.job_id, e.name, "timed_out", f"timeout after {e.timeout_sec:.1f}s", persist, e
        )

    def _apply_cancelled(self, e: JobCancelled, *, persist: bool) -> None:
        self._set_terminal(e.job_id, e.name, "cancelled", None, persist, e)

    def _set_terminal(
        self, job_id: str, name: str, status: str, error: str | None, persist: bool, event: Any
    ) -> None:
        with self._lock:
            rec = self._ensure(job_id, name)
            rec.status = status
            rec.error = error
            rec.finished_at = datetime.utcnow()
            if status == "finished":
                rec.progress = 1.0
        if persist:
            self._persist(event)

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
