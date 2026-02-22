#commit и версия
from __future__ import annotations

import time
import sys

from app.core.events import EventBus
from app.core.events.job_events import JobLogLine
from app.core.jobs.job_runner import JobRunner


def test_job_runner_routes_stdout_per_thread() -> None:
    bus = EventBus()
    runner = JobRunner(bus, max_workers=2)
    events: list[JobLogLine] = []
    bus.subscribe(JobLogLine, events.append)

    def make_job(prefix: str):
        def _job(_token, _progress):
            for i in range(20):
                print(f"{prefix}-{i}")
                time.sleep(0.001)
            return prefix

        return _job

    h1 = runner.submit("job-a", make_job("A"))
    h2 = runner.submit("job-b", make_job("B"))

    assert h1.future.result(timeout=5) == "A"
    assert h2.future.result(timeout=5) == "B"

    time.sleep(0.2)
    by_job: dict[str, str] = {}
    for e in events:
        by_job[e.job_id] = by_job.get(e.job_id, "") + "\n" + e.line

    assert len(by_job) >= 2
    texts = list(by_job.values())
    assert any("A-0" in t and "B-0" not in t for t in texts)
    assert any("B-0" in t and "A-0" not in t for t in texts)


def test_job_runner_restores_stdio_on_shutdown() -> None:
    bus = EventBus()
    original_out = sys.stdout
    original_err = sys.stderr

    runner = JobRunner(bus, max_workers=1)
    runner.shutdown()

    assert sys.stdout is original_out
    assert sys.stderr is original_err
