from __future__ import annotations

import pytest

from app.core.events import TrainingProgress

try:
    from app.ui.views.training.view_model import TrainingViewModel
except ImportError as exc:  # pragma: no cover - environment-specific skip
    pytest.skip(
        f"TrainingViewModel import unavailable in this environment: {exc}", allow_module_level=True
    )


class _Bus:
    def __init__(self) -> None:
        self.events = []

    def publish(self, event) -> None:
        self.events.append(event)


class _Container:
    def __init__(self, bus: _Bus) -> None:
        self.event_bus = bus


def _mk_vm_for_unit_tests() -> tuple[TrainingViewModel, _Bus]:
    vm = TrainingViewModel.__new__(TrainingViewModel)
    bus = _Bus()
    vm._container = _Container(bus)
    vm._active_job_id = "job-1"
    vm._last_job_progress_ts = 0.0
    vm._last_job_progress_key = None
    vm._last_log_line = None
    vm._last_log_repeat_count = 0
    vm._emit_on_ui_thread = lambda fn: None
    vm._signals = type(
        "_S", (), {"progress_updated": type("_P", (), {"emit": lambda *a, **k: None})()}
    )()
    return vm, bus


def test_training_progress_is_throttled_for_identical_updates(monkeypatch) -> None:
    vm, bus = _mk_vm_for_unit_tests()

    t = {"now": 10.0}
    monkeypatch.setattr("app.ui.views.training.view_model.time.monotonic", lambda: t["now"])

    vm._on_training_progress(TrainingProgress(fraction=0.5, message="same"))
    vm._on_training_progress(TrainingProgress(fraction=0.5, message="same"))
    assert len(bus.events) == 1

    t["now"] = 10.2
    vm._on_training_progress(TrainingProgress(fraction=0.5, message="same"))
    assert len(bus.events) == 2


def test_should_publish_log_line_limits_repeated_lines() -> None:
    vm, _ = _mk_vm_for_unit_tests()

    results = [vm._should_publish_log_line("line") for _ in range(5)]
    assert results == [True, True, True, False, False]

    assert vm._should_publish_log_line("other") is True
