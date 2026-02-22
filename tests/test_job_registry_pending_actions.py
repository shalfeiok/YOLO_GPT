#commit и версия
from __future__ import annotations

from app.core.events import EventBus
from app.core.events.job_events import JobLogLine, JobProgress, JobStarted
from app.core.jobs import JobRegistry


def test_set_rerun_before_start_is_attached_on_start() -> None:
    bus = EventBus()
    registry = JobRegistry(bus)

    called = {"n": 0}

    def rerun() -> None:
        called["n"] += 1

    registry.set_rerun("j1", rerun)
    bus.publish(JobStarted(job_id="j1", name="task"))

    rec = registry.get("j1")
    assert rec is not None
    assert rec.rerun is not None
    rec.rerun()
    assert called["n"] == 1


def test_set_cancel_before_start_is_attached_on_start() -> None:
    bus = EventBus()
    registry = JobRegistry(bus)

    called = {"n": 0}

    def cancel() -> None:
        called["n"] += 1

    registry.set_cancel("j2", cancel)
    bus.publish(JobStarted(job_id="j2", name="task"))

    rec = registry.get("j2")
    assert rec is not None
    assert rec.cancel is not None
    rec.cancel()
    assert called["n"] == 1


def test_setters_ignore_empty_job_id() -> None:
    bus = EventBus()
    registry = JobRegistry(bus)

    registry.set_rerun("", lambda: None)
    registry.set_cancel("", lambda: None)

    assert registry._pending_rerun == {}
    assert registry._pending_cancel == {}


def test_pending_callbacks_are_bounded_by_max_jobs() -> None:
    bus = EventBus()
    registry = JobRegistry(bus, max_jobs=2)

    registry.set_rerun("a", lambda: None)
    registry.set_rerun("b", lambda: None)
    registry.set_rerun("c", lambda: None)
    registry.set_cancel("x", lambda: None)
    registry.set_cancel("y", lambda: None)
    registry.set_cancel("z", lambda: None)

    assert len(registry._pending_rerun) <= 2
    assert len(registry._pending_cancel) <= 2


def test_duplicate_job_started_does_not_reset_state() -> None:
    bus = EventBus()
    registry = JobRegistry(bus)

    bus.publish(JobStarted(job_id="dup", name="task"))
    bus.publish(JobProgress(job_id="dup", name="task", progress=0.5, message="half"))
    bus.publish(JobLogLine(job_id="dup", name="task", line="hello"))

    # duplicate start should not wipe state
    bus.publish(JobStarted(job_id="dup", name="task-renamed"))

    rec = registry.get("dup")
    assert rec is not None
    assert rec.name == "task-renamed"
    assert rec.status == "running"
    assert rec.progress == 0.5
    assert rec.message == "half"
    assert rec.logs == ["hello"]


def test_close_unsubscribes_registry_handlers() -> None:
    bus = EventBus()
    registry = JobRegistry(bus)

    registry.close()
    bus.publish(JobStarted(job_id="closed", name="task"))

    assert registry.get("closed") is None


def test_repeated_log_lines_are_collapsed() -> None:
    bus = EventBus()
    registry = JobRegistry(bus)

    bus.publish(JobStarted(job_id="j-log", name="task"))
    bus.publish(JobLogLine(job_id="j-log", name="task", line="same"))
    bus.publish(JobLogLine(job_id="j-log", name="task", line="same"))
    bus.publish(JobLogLine(job_id="j-log", name="task", line="other"))

    rec = registry.get("j-log")
    assert rec is not None
    assert rec.logs == ["same", "other"]
