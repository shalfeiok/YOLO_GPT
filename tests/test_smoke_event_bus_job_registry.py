from app.core.events.event_bus import EventBus
from app.core.events.job_events import JobLogLine, JobStarted
from app.core.jobs.job_registry import JobRegistry


class DemoEvent:
    def __init__(self, value: int) -> None:
        self.value = value


def test_event_bus_subscribe_and_publish() -> None:
    bus = EventBus()
    received: list[int] = []

    bus.subscribe(DemoEvent, lambda event: received.append(event.value))
    bus.publish(DemoEvent(7))

    assert received == [7]


def test_job_registry_tracks_logs_with_limit() -> None:
    bus = EventBus()
    registry = JobRegistry(bus, max_log_lines=2)

    bus.publish(JobStarted(job_id="job-1", name="demo-job"))
    bus.publish(JobLogLine(job_id="job-1", name="demo-job", line="line-1"))
    bus.publish(JobLogLine(job_id="job-1", name="demo-job", line="line-2"))
    bus.publish(JobLogLine(job_id="job-1", name="demo-job", line="line-3"))

    snapshot = registry.get("job-1")
    assert snapshot is not None
    assert snapshot.logs == ["line-2", "line-3"]
