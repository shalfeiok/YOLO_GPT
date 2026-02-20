from __future__ import annotations

import time

import pytest

from app.core.events import EventBus
from app.core.events.job_events import JobFailed, JobRetrying
from app.core.errors import IntegrationError, ValidationError
from app.core.jobs.job_runner import JobRunner


def test_job_runner_retries_only_integration_infrastructure_errors() -> None:
    bus = EventBus()
    runner = JobRunner(bus, max_workers=1)

    retry_events: list[JobRetrying] = []
    failed_events: list[JobFailed] = []

    bus.subscribe(JobRetrying, retry_events.append)
    bus.subscribe(JobFailed, failed_events.append)

    attempts = {"n": 0}

    def flaky(_token, _progress):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise IntegrationError("network")
        return "ok"

    handle = runner.submit("flaky", flaky, retries=3, retry_backoff_sec=0.01, retry_jitter=0.0)
    assert handle.future.result(timeout=2.0) == "ok"

    assert len(retry_events) == 1
    assert retry_events[0].attempt == 1

    # ValidationError should NOT be retried
    retry_events.clear()
    failed_events.clear()

    def invalid(_token, _progress):
        raise ValidationError("bad input")

    handle2 = runner.submit("invalid", invalid, retries=3, retry_backoff_sec=0.01)
    with pytest.raises(ValidationError):
        handle2.future.result(timeout=2.0)

    assert len(retry_events) == 0
    assert len(failed_events) == 1


def test_job_runner_retry_deadline_prevents_retries() -> None:
    bus = EventBus()
    runner = JobRunner(bus, max_workers=1)

    retry_events: list[JobRetrying] = []
    bus.subscribe(JobRetrying, retry_events.append)

    def always_fails(_token, _progress):
        raise IntegrationError("down")

    # Deadline 0 => no retries
    handle = runner.submit(
        "deadline",
        always_fails,
        retries=5,
        retry_backoff_sec=0.01,
        retry_deadline_sec=0.0,
    )
    with pytest.raises(IntegrationError):
        handle.future.result(timeout=2.0)

    assert retry_events == []
