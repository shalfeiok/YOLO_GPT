from __future__ import annotations

import threading

import pytest

from app.core.errors import CancelledError
from app.core.events import EventBus
from app.core.events.job_events import JobCancelled
from app.core.jobs.job_runner import JobRunner


def test_job_runner_emits_single_cancel_event_when_pre_cancelled() -> None:
    bus = EventBus()
    runner = JobRunner(bus, max_workers=1)

    cancelled_events: list[JobCancelled] = []
    bus.subscribe(JobCancelled, cancelled_events.append)

    blocker_released = threading.Event()

    def blocker(_token, _progress):
        blocker_released.wait(timeout=2.0)
        return "done"

    running = runner.submit("blocker", blocker)

    def should_not_run(_token, _progress):
        pytest.fail("job function must not run when token is cancelled before start")

    handle = runner.submit("cancelled", should_not_run)
    handle.cancel()

    # release first job so second can be dequeued and immediately observe cancellation
    blocker_released.set()
    assert running.future.result(timeout=2.0) == "done"

    with pytest.raises(CancelledError):
        handle.future.result(timeout=2.0)

    assert len(cancelled_events) == 1


def test_job_runner_emits_single_cancel_event_when_cancelled_during_run() -> None:
    bus = EventBus()
    runner = JobRunner(bus, max_workers=1)

    cancelled_events: list[JobCancelled] = []
    bus.subscribe(JobCancelled, cancelled_events.append)

    gate = threading.Event()

    def cancellable_job(_token, _progress):
        gate.wait(timeout=2.0)
        return "done"

    handle = runner.submit("cancel-mid", cancellable_job)
    handle.cancel()
    gate.set()

    with pytest.raises(CancelledError):
        handle.future.result(timeout=2.0)

    assert len(cancelled_events) == 1
