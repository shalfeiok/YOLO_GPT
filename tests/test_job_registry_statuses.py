from __future__ import annotations

from app.core.events import EventBus
from app.core.events.job_events import JobRetrying, JobStarted, JobTimedOut
from app.core.jobs import JobRegistry


def test_job_registry_marks_retrying() -> None:
    bus = EventBus()
    reg = JobRegistry(bus)

    bus.publish(JobStarted(job_id="1", name="task"))
    bus.publish(JobRetrying(job_id="1", name="task", attempt=1, max_attempts=3, error="boom"))

    rec = reg.get("1")
    assert rec is not None
    assert rec.status == "retrying"
    assert rec.message is not None
    assert "retry 1/3" in rec.message


def test_job_registry_marks_timed_out() -> None:
    bus = EventBus()
    reg = JobRegistry(bus)

    bus.publish(JobStarted(job_id="2", name="task"))
    bus.publish(JobTimedOut(job_id="2", name="task", timeout_sec=12.34))

    rec = reg.get("2")
    assert rec is not None
    assert rec.status == "timed_out"
    assert rec.error is not None
    assert "timeout" in rec.error
