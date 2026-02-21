from __future__ import annotations

import queue

import pytest

from app.core.events import EventBus
from app.core.events.job_events import JobFailed, JobFinished
from app.core.jobs.process_job_runner import ProcessJobRunner


class _FakeProcess:
    def __init__(self, target, args, daemon=True):
        self._target = target
        self._args = args
        self._alive = False

    def start(self):
        # Simulate a process that exits before posting anything to the queue.
        self._alive = False

    def is_alive(self):
        return self._alive

    def terminate(self):
        self._alive = False

    def join(self, timeout=None):
        return None


class _FakeCtx:
    def Event(self):
        from threading import Event

        return Event()

    def Queue(self):
        return queue.Queue()

    def Process(self, target, args, daemon=True):
        return _FakeProcess(target=target, args=args, daemon=daemon)


def test_process_job_runner_fails_if_child_exits_without_result(monkeypatch) -> None:
    bus = EventBus()
    runner = ProcessJobRunner(bus, max_workers=1)
    monkeypatch.setattr(runner, "_ctx", _FakeCtx())

    failed: list[JobFailed] = []
    finished: list[JobFinished] = []
    bus.subscribe(JobFailed, failed.append)
    bus.subscribe(JobFinished, finished.append)

    def _dummy(_cancel_evt, _progress):
        return "ok"

    handle = runner.submit("empty-child", _dummy)
    with pytest.raises(RuntimeError, match="without a result payload"):
        handle.future.result(timeout=2)

    assert len(failed) == 1
    assert finished == []
