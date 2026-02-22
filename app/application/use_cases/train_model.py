"""Train model use case.

This wraps the low-level trainer service behind a stable, UI-friendly API.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
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


class TrainingProfile(str, Enum):
    DETERMINISTIC = "deterministic"
    FAST_LOCAL = "fast_local"


@dataclass(frozen=True, slots=True)
class TrainingRunSpec:
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
    cache: bool | str
    deterministic: bool
    seed: int
    output_dir: Path
    advanced_options: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "data_yaml": str(self.data_yaml),
            "model_name": self.model_name,
            "epochs": self.epochs,
            "batch": self.batch,
            "imgsz": self.imgsz,
            "device": self.device,
            "patience": self.patience,
            "project": str(self.project),
            "weights_path": None if self.weights_path is None else str(self.weights_path),
            "workers": self.workers,
            "optimizer": self.optimizer,
            "cache": self.cache,
            "deterministic": self.deterministic,
            "seed": self.seed,
            "output_dir": str(self.output_dir),
            "advanced_options": dict(self.advanced_options),
        }


def build_training_run_spec(request: TrainModelRequest, profile: TrainingProfile | None = None) -> TrainingRunSpec:
    adv = dict(request.advanced_options)
    cache: bool | str = adv.get("cache", False)
    deterministic = bool(adv.get("deterministic", False))
    seed = int(adv.get("seed", 0))
    workers = int(request.workers)

    if profile == TrainingProfile.DETERMINISTIC:
        deterministic = True
        seed = 42 if seed <= 0 else seed
        workers = min(max(workers, 0), 2)
        cache = "disk" if not cache else cache
    elif profile == TrainingProfile.FAST_LOCAL:
        deterministic = False
        workers = max(workers, 4)
        cache = True if cache is False else cache

    adv["cache"] = cache
    adv["deterministic"] = deterministic
    adv["seed"] = seed

    return TrainingRunSpec(
        data_yaml=request.data_yaml,
        model_name=request.model_name,
        epochs=request.epochs,
        batch=request.batch,
        imgsz=request.imgsz,
        device=request.device,
        patience=request.patience,
        project=request.project,
        weights_path=request.weights_path,
        workers=workers,
        optimizer=request.optimizer,
        cache=cache,
        deterministic=deterministic,
        seed=seed,
        output_dir=request.project,
        advanced_options=adv,
    )


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
        profile_raw = request.advanced_options.get("run_profile") if isinstance(request.advanced_options, dict) else None
        profile = TrainingProfile(profile_raw) if profile_raw in {p.value for p in TrainingProfile} else None
        spec = build_training_run_spec(request, profile=profile)

        log.info(
            "Training requested",
            extra={
                "event": "training_requested",
                "model": spec.model_name,
                "project": str(spec.project),
                "training_profile": None if profile is None else profile.value,
                "training_spec": spec.to_dict(),
            },
        )
        if self._bus is not None:
            self._bus.publish(
                TrainingStarted(model_name=spec.model_name, epochs=spec.epochs, project=spec.project)
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
                data_yaml=spec.data_yaml,
                model_name=spec.model_name,
                epochs=spec.epochs,
                batch=spec.batch,
                imgsz=spec.imgsz,
                device=spec.device,
                patience=spec.patience,
                project=spec.project,
                on_progress=_progress,
                console_queue=console_queue,
                weights_path=spec.weights_path,
                workers=spec.workers,
                optimizer=spec.optimizer,
                advanced_options=spec.advanced_options,
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
