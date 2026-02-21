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


class _DelayedResultQueue:
    def __init__(self) -> None:
        self._calls = 0

    def get(self, timeout=None):
        self._calls += 1
        if self._calls == 1:
            raise queue.Empty
        return ("result", "ok")


class _DeadThenDrainProcess(_FakeProcess):
    @property
    def exitcode(self):
        return 0


class _FakeDrainCtx:
    def Event(self):
        from threading import Event

        return Event()

    def Queue(self):
        return _DelayedResultQueue()

    def Process(self, target, args, daemon=True):
        return _DeadThenDrainProcess(target=target, args=args, daemon=daemon)


def test_process_job_runner_reads_late_result_after_child_exit(monkeypatch) -> None:
    bus = EventBus()
    runner = ProcessJobRunner(bus, max_workers=1)
    monkeypatch.setattr(runner, "_ctx", _FakeDrainCtx())

    finished: list[JobFinished] = []
    failed: list[JobFailed] = []
    bus.subscribe(JobFinished, finished.append)
    bus.subscribe(JobFailed, failed.append)

    def _dummy(_cancel_evt, _progress):
        return "ok"

    handle = runner.submit("late-result", _dummy)
    assert handle.future.result(timeout=2) == "ok"

    assert len(finished) == 1
    assert failed == []


class _NonZeroExitProcess(_FakeProcess):
    @property
    def exitcode(self):
        return 137


class _NonZeroExitCtx(_FakeCtx):
    def Process(self, target, args, daemon=True):
        return _NonZeroExitProcess(target=target, args=args, daemon=daemon)


def test_process_job_runner_reports_exit_code_when_payload_missing(monkeypatch) -> None:
    bus = EventBus()
    runner = ProcessJobRunner(bus, max_workers=1)
    monkeypatch.setattr(runner, "_ctx", _NonZeroExitCtx())

    failed: list[JobFailed] = []
    bus.subscribe(JobFailed, failed.append)

    def _dummy(_cancel_evt, _progress):
        return "ok"

    handle = runner.submit("exitcode-missing-payload", _dummy)
    with pytest.raises(RuntimeError, match=r"exited with code 137"):
        handle.future.result(timeout=2)

    assert len(failed) == 1
    assert "code 137" in failed[0].error


class _TrackableQueue(_DelayedResultQueue):
    def __init__(self) -> None:
        super().__init__()
        self.closed = False
        self.joined = False

    def close(self):
        self.closed = True

    def join_thread(self):
        self.joined = True


class _TrackableCtx(_FakeDrainCtx):
    def __init__(self) -> None:
        self.last_queue: _TrackableQueue | None = None

    def Queue(self):
        q = _TrackableQueue()
        self.last_queue = q
        return q


def test_process_job_runner_closes_queue_on_exit(monkeypatch) -> None:
    bus = EventBus()
    runner = ProcessJobRunner(bus, max_workers=1)
    ctx = _TrackableCtx()
    monkeypatch.setattr(runner, "_ctx", ctx)

    def _dummy(_cancel_evt, _progress):
        return "ok"

    handle = runner.submit("queue-cleanup", _dummy)
    assert handle.future.result(timeout=2) == "ok"

    assert ctx.last_queue is not None
    assert ctx.last_queue.closed is True
    assert ctx.last_queue.joined is True


class _UnknownKindQueue:
    def get(self, timeout=None):
        return ("mystery-kind", {"x": 1})

    def close(self):
        return None

    def join_thread(self):
        return None


class _UnknownKindCtx(_FakeDrainCtx):
    def Queue(self):
        return _UnknownKindQueue()


def test_process_job_runner_fails_on_unknown_child_message_kind(monkeypatch) -> None:
    bus = EventBus()
    runner = ProcessJobRunner(bus, max_workers=1)
    monkeypatch.setattr(runner, "_ctx", _UnknownKindCtx())

    failed: list[JobFailed] = []
    finished: list[JobFinished] = []
    bus.subscribe(JobFailed, failed.append)
    bus.subscribe(JobFinished, finished.append)

    def _dummy(_cancel_evt, _progress):
        return "ok"

    handle = runner.submit("unknown-kind", _dummy)
    with pytest.raises(RuntimeError, match="Unknown child message kind"):
        handle.future.result(timeout=2)

    assert len(failed) == 1
    assert "Unknown child message kind" in failed[0].error
    assert finished == []
