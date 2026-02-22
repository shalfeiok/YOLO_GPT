from app.core.events.event_bus import EventBus
from app.core.jobs.job_registry import JobRegistry


def test_event_bus_subscribe_and_publish() -> None:
    bus = EventBus()
    received: list[int] = []

    bus.subscribe("demo", lambda payload: received.append(payload["value"]))
    bus.publish("demo", {"value": 7})

    assert received == [7]


def test_job_registry_create_and_log_limit() -> None:
    registry = JobRegistry(max_log_lines=2)

    job_id = registry.register("demo-job")
    registry.append_log(job_id, "line-1")
    registry.append_log(job_id, "line-2")
    registry.append_log(job_id, "line-3")

    snapshot = registry.snapshot(job_id)
    assert snapshot is not None
    assert snapshot.logs == ["line-2", "line-3"]
