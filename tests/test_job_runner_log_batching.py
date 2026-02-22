from __future__ import annotations

import time

from app.core.events import EventBus
from app.core.events.job_events import JobLogLine
from app.core.jobs.job_runner import JobRunner


def test_job_runner_batches_log_lines() -> None:
    bus = EventBus()
    runner = JobRunner(bus, max_workers=1)
    logs: list[str] = []
    bus.subscribe(JobLogLine, lambda e: logs.append(e.line))

    def job(token, progress):
        for i in range(120):
            print(f"line-{i}")
        return 1

    handle = runner.submit("log-batch", job)
    assert handle.future.result(timeout=10) == 1
    time.sleep(0.2)

    assert logs
    assert len(logs) < 120
    assert any("\n" in chunk for chunk in logs)
