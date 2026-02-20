from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.application.use_cases.train_model import TrainModelRequest, TrainModelUseCase
from app.core.events import (
    EventBus,
    TrainingCancelled,
    TrainingFailed,
    TrainingFinished,
    TrainingProgress,
    TrainingStarted,
)


@dataclass
class _FakeTrainer:
    """Minimal trainer stub for application-layer tests."""

    should_fail: bool = False
    should_cancel: bool = False
    stopped: bool = False

    def train(
        self,
        *,
        data_yaml: Path,
        model_name: str,
        epochs: int,
        batch: int,
        imgsz: int,
        device: str,
        patience: int,
        project: Path,
        on_progress,
        console_queue,
        weights_path: Path | None,
        workers: int,
        optimizer: str,
        advanced_options: dict,
    ) -> Path | None:
        # Emit a couple of progress updates.
        on_progress(0.1, "epoch 1")
        on_progress(0.5, "epoch 2")

        if self.should_cancel:
            on_progress(-1.0, "cancelled")
            return None

        if self.should_fail:
            raise RuntimeError("boom")

        on_progress(1.0, "done")
        return project / "best.pt"

    def stop(self) -> None:
        self.stopped = True


def _request(tmp_path: Path) -> TrainModelRequest:
    return TrainModelRequest(
        data_yaml=tmp_path / "data.yaml",
        model_name="yolov8n",
        epochs=3,
        batch=4,
        imgsz=640,
        device="cpu",
        patience=10,
        project=tmp_path,
        weights_path=None,
        workers=0,
        optimizer="auto",
        advanced_options={},
    )


def test_train_use_case_publishes_events_in_order(tmp_path: Path) -> None:
    bus = EventBus()
    trainer = _FakeTrainer()
    uc = TrainModelUseCase(trainer=trainer, event_bus=bus)

    seen: list[object] = []
    bus.subscribe(TrainingStarted, seen.append)
    bus.subscribe(TrainingProgress, seen.append)
    bus.subscribe(TrainingFinished, seen.append)

    result = uc.execute(_request(tmp_path))

    assert result == tmp_path / "best.pt"
    assert isinstance(seen[0], TrainingStarted)
    assert any(isinstance(e, TrainingProgress) for e in seen)
    assert isinstance(seen[-1], TrainingFinished)


def test_train_use_case_publishes_failed_event(tmp_path: Path) -> None:
    bus = EventBus()
    trainer = _FakeTrainer(should_fail=True)
    uc = TrainModelUseCase(trainer=trainer, event_bus=bus)

    failed: list[TrainingFailed] = []
    bus.subscribe(TrainingFailed, failed.append)

    with pytest.raises(RuntimeError, match="boom"):
        uc.execute(_request(tmp_path))

    assert len(failed) == 1
    assert isinstance(failed[0].error, RuntimeError)


def test_train_use_case_publishes_cancelled_event_and_no_finished(tmp_path: Path) -> None:
    bus = EventBus()
    trainer = _FakeTrainer(should_cancel=True)
    uc = TrainModelUseCase(trainer=trainer, event_bus=bus)

    seen: list[object] = []
    bus.subscribe(TrainingStarted, seen.append)
    bus.subscribe(TrainingProgress, seen.append)
    bus.subscribe(TrainingCancelled, seen.append)
    bus.subscribe(TrainingFinished, seen.append)

    result = uc.execute(_request(tmp_path))

    assert result is None
    assert any(isinstance(e, TrainingCancelled) for e in seen)
    assert not any(isinstance(e, TrainingFinished) for e in seen)


def test_train_use_case_stop_delegates_to_trainer() -> None:
    bus = EventBus()
    trainer = _FakeTrainer()
    uc = TrainModelUseCase(trainer=trainer, event_bus=bus)

    uc.stop()

    assert trainer.stopped is True
