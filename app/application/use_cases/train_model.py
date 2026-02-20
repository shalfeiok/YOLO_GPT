"""Train model use case.

This wraps the low-level trainer service behind a stable, UI-friendly API.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from collections.abc import Callable
from typing import Any, Protocol

from app.core.events import (
    EventBus,
    TrainingCancelled,
    TrainingFailed,
    TrainingFinished,
    TrainingProgress,
    TrainingStarted,
)
from app.core.observability.timing import timed


log = logging.getLogger(__name__)


class TrainerPort(Protocol):
    """Port the application layer needs from the training service."""

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
        on_progress: Callable[[float, str], None],
        console_queue: Any,
        weights_path: Path | None,
        workers: int,
        optimizer: str,
        advanced_options: dict[str, Any],
    ) -> Path | None:
        ...

    def stop(self) -> None:
        ...


@dataclass(frozen=True, slots=True)
class TrainModelRequest:
    data_yaml: Path
    model_name: str
    epochs: int
    batch: int
    imgsz: int
    device: str
    patience: int
    project: Path
    weights_path: Path | None
    workers: int
    optimizer: str
    advanced_options: dict[str, Any]


class TrainModelUseCase:
    """Orchestrates model training."""

    def __init__(self, trainer: TrainerPort, event_bus: EventBus | None = None) -> None:
        self._trainer = trainer
        self._bus = event_bus

    @timed("use_case.train_model")
    def execute(
        self,
        request: TrainModelRequest,
        *,
        on_progress: Callable[[float, str], None] | None = None,
        console_queue: Any = None,
    ) -> Path | None:
        log.info(
            "Training requested",
            extra={"event": "training_requested", "model": request.model_name, "project": str(request.project)},
        )
        if self._bus is not None:
            self._bus.publish(
                TrainingStarted(model_name=request.model_name, epochs=request.epochs, project=request.project)
            )

        cancelled = False

        def _progress(fraction: float, message: str) -> None:
            nonlocal cancelled
            # Preserve existing callback semantics for UI.
            if on_progress:
                on_progress(fraction, message)
            if self._bus is None:
                return
            if fraction < 0:
                cancelled = True
                self._bus.publish(TrainingCancelled(message=message))
            else:
                self._bus.publish(TrainingProgress(fraction=fraction, message=message))

        try:
            best = self._trainer.train(
                data_yaml=request.data_yaml,
                model_name=request.model_name,
                epochs=request.epochs,
                batch=request.batch,
                imgsz=request.imgsz,
                device=request.device,
                patience=request.patience,
                project=request.project,
                on_progress=_progress,
                console_queue=console_queue,
                weights_path=request.weights_path,
                workers=request.workers,
                optimizer=request.optimizer,
                advanced_options=request.advanced_options,
            )
        except Exception as e:  # noqa: BLE001 - use-case boundary
            if self._bus is not None:
                self._bus.publish(TrainingFailed(error=e))
            log.exception(
                "Training failed",
                extra={"event": "training_failed", "model": request.model_name, "project": str(request.project)},
            )
            raise
        else:
            if cancelled:
                log.info(
                    "Training cancelled",
                    extra={"event": "training_cancelled", "model": request.model_name, "project": str(request.project)},
                )
                return None
            if self._bus is not None:
                self._bus.publish(TrainingFinished(best_weights_path=best))
            log.info(
                "Training finished",
                extra={"event": "training_finished", "model": request.model_name, "project": str(request.project)},
            )
            return best

    def stop(self) -> None:
        self._trainer.stop()
