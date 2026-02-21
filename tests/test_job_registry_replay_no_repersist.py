from __future__ import annotations

import json
from pathlib import Path

from app.core.events import EventBus
from app.core.events.job_events import JobFinished, JobProgress, JobStarted
from app.core.jobs import JobRegistry, JsonlJobEventStore


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8").splitlines())


def test_replay_does_not_append_duplicate_events(tmp_path: Path) -> None:
    store = JsonlJobEventStore(tmp_path / "jobs.jsonl")

    bus = EventBus()
    _ = JobRegistry(bus, store=store, replay_on_start=False)
    bus.publish(JobStarted(job_id="1", name="task"))
    bus.publish(JobProgress(job_id="1", name="task", progress=0.2, message="x"))
    bus.publish(JobFinished(job_id="1", name="task", result=None))

    before = _line_count(store.path)
    assert before == 3

    bus2 = EventBus()
    _ = JobRegistry(bus2, store=store, replay_on_start=True)

    after = _line_count(store.path)
    assert after == before

    # sanity: still valid JSONL
    lines = store.path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        rec = json.loads(line)
        assert "type" in rec and "data" in rec
