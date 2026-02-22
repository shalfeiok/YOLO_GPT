from __future__ import annotations

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


def replay_records(registry: "JobRegistry") -> None:
    assert registry._store is not None
    for rec in registry._store.load():
        t = rec.get("type")
        data = rec.get("data") or {}
        if not isinstance(data, dict) or not isinstance(t, str):
            continue
        job_id = str(data.get("job_id", ""))
        name = str(data.get("name", ""))
        if not job_id or not name:
            continue

        if t == "JobStarted":
            registry._apply_started(JobStarted(job_id=job_id, name=name), persist=False)
        elif t == "JobProgress":
            try:
                progress = float(data.get("progress", 0.0))
            except Exception:
                progress = 0.0
            registry._apply_progress(
                JobProgress(job_id=job_id, name=name, progress=progress, message=data.get("message")),
                persist=False,
            )
        elif t == "JobLogLine":
            line = str(data.get("line", ""))
            if line:
                registry._apply_log(JobLogLine(job_id=job_id, name=name, line=line), persist=False)
        elif t == "JobFinished":
            registry._apply_finished(JobFinished(job_id=job_id, name=name, result=None), persist=False)
        elif t == "JobFailed":
            registry._apply_failed(JobFailed(job_id=job_id, name=name, error=str(data.get("error", ""))), persist=False)
        elif t == "JobCancelled":
            registry._apply_cancelled(JobCancelled(job_id=job_id, name=name), persist=False)
        elif t == "JobRetrying":
            try:
                attempt = int(data.get("attempt", 1))
                max_attempts = int(data.get("max_attempts", attempt))
            except Exception:
                attempt, max_attempts = 1, 1
            registry._apply_retrying(
                JobRetrying(job_id=job_id, name=name, attempt=attempt, max_attempts=max_attempts, error=str(data.get("error", ""))),
                persist=False,
            )
        elif t == "JobTimedOut":
            try:
                timeout_sec = float(data.get("timeout_sec", 0.0))
            except Exception:
                timeout_sec = 0.0
            registry._apply_timed_out(
                JobTimedOut(job_id=job_id, name=name, timeout_sec=timeout_sec),
                persist=False,
            )

    with registry._lock:
        registry._purge_if_needed()
