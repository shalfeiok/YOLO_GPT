from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.application.settings.models import TrainingSettings


@dataclass(frozen=True, slots=True)
class TrainingLaunchArgs:
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
    log_path: Path
    advanced_options: dict[str, Any]

    def as_view_model_kwargs(self) -> dict[str, Any]:
        return {
            "data_yaml": self.data_yaml,
            "model_name": self.model_name,
            "epochs": self.epochs,
            "batch": self.batch,
            "imgsz": self.imgsz,
            "device": self.device,
            "patience": self.patience,
            "project": self.project,
            "weights_path": self.weights_path,
            "workers": self.workers,
            "optimizer": self.optimizer,
            "log_path": self.log_path,
            "advanced_options": dict(self.advanced_options),
        }


def build_training_launch_args(
    settings: TrainingSettings,
    *,
    data_yaml: Path,
    log_path: Path,
) -> TrainingLaunchArgs:
    return TrainingLaunchArgs(
        data_yaml=data_yaml,
        model_name=settings.model_name,
        epochs=settings.epochs,
        batch=settings.batch,
        imgsz=settings.imgsz,
        device=settings.device,
        patience=settings.patience,
        project=Path(settings.project),
        weights_path=Path(settings.weights_path) if settings.weights_path else None,
        workers=settings.workers,
        optimizer=settings.optimizer,
        log_path=log_path,
        advanced_options=dict(settings.advanced_options),
    )
