from __future__ import annotations

from app.core.events import EventBus
from app.core.events.job_events import JobStarted
from app.core.jobs import JobRegistry


def test_registry_get_returns_snapshot_copy() -> None:
    bus = EventBus()
    registry = JobRegistry(bus)

    bus.publish(JobStarted(job_id="a", name="task"))

    rec = registry.get("a")
    assert rec is not None
    rec.logs.append("mutated")

    rec2 = registry.get("a")
    assert rec2 is not None
    assert rec2.logs == []


def test_registry_list_returns_snapshot_copies() -> None:
    bus = EventBus()
    registry = JobRegistry(bus)

    bus.publish(JobStarted(job_id="a", name="task"))

    records = registry.list()
    records[0].logs.append("mutated")

    fresh = registry.list()
    assert fresh[0].logs == []
