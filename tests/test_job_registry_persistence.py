from __future__ import annotations

from pathlib import Path

from app.core.events import EventBus
from app.core.events.job_events import JobFinished, JobLogLine, JobProgress, JobStarted
from app.core.jobs import JobRegistry, JsonlJobEventStore


def test_job_registry_replays_persisted_events(tmp_path: Path) -> None:
    bus = EventBus()
    store = JsonlJobEventStore(tmp_path / "jobs.jsonl")

    reg1 = JobRegistry(bus, store=store, replay_on_start=False)
    bus.publish(JobStarted(job_id="1", name="task"))
    bus.publish(JobProgress(job_id="1", name="task", progress=0.5, message="half"))
    bus.publish(JobLogLine(job_id="1", name="task", line="hello"))
    bus.publish(JobFinished(job_id="1", name="task", result=None))

    # New registry should replay from store
    bus2 = EventBus()
    reg2 = JobRegistry(bus2, store=store, replay_on_start=True)

    rec = reg2.get("1")
    assert rec is not None
    assert rec.name == "task"
    assert rec.status == "finished"
    assert rec.progress == 1.0
    assert rec.message == "half"
    assert rec.logs[-1] == "hello"
