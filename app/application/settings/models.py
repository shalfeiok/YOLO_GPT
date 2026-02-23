from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import (
    DEFAULT_BATCH,
    DEFAULT_CONFIDENCE,
    DEFAULT_DATASET1,
    DEFAULT_DEVICE,
    DEFAULT_EPOCHS,
    DEFAULT_IMGSZ,
    DEFAULT_IOU_THRESH,
    DEFAULT_PATIENCE,
    DEFAULT_WORKERS,
    PROJECT_ROOT,
)
from app.domain.training_config import ADVANCED_DEFAULTS, TrainingConfig


@dataclass(frozen=True, slots=True)
class TrainingSettings:
    model_name: str = "yolo11n.pt"
    weights_path: str | None = None
    dataset_paths: tuple[str, ...] = field(default_factory=tuple)
    project: str = str(PROJECT_ROOT / "runs" / "train")
    device: str = DEFAULT_DEVICE
    epochs: int = DEFAULT_EPOCHS
    batch: int = DEFAULT_BATCH
    imgsz: int = DEFAULT_IMGSZ
    patience: int = DEFAULT_PATIENCE
    workers: int = DEFAULT_WORKERS
    optimizer: str = "auto"
    advanced_options: dict[str, Any] = field(default_factory=lambda: dict(ADVANCED_DEFAULTS))

    @classmethod
    def default(cls) -> "TrainingSettings":
        return cls(dataset_paths=(str(DEFAULT_DATASET1),))

    @classmethod
    def from_training_config(cls, cfg: TrainingConfig) -> "TrainingSettings":
        adv = dict(ADVANCED_DEFAULTS)
        adv.update(dict(cfg.advanced_options or {}))
        return cls(
            model_name=cfg.model_name,
            weights_path=cfg.weights_path,
            dataset_paths=tuple(cfg.dataset_paths),
            project=cfg.project,
            device=cfg.device,
            epochs=cfg.epochs,
            batch=cfg.batch,
            imgsz=cfg.imgsz,
            patience=cfg.patience,
            workers=cfg.workers,
            optimizer=cfg.optimizer,
            advanced_options=adv,
        )

    def to_training_config(self) -> TrainingConfig:
        return TrainingConfig.from_current_state(
            {
                "model_name": self.model_name,
                "weights_path": self.weights_path,
                "dataset_paths": list(self.dataset_paths),
                "project": self.project,
                "device": self.device,
                "epochs": self.epochs,
                "batch": self.batch,
                "imgsz": self.imgsz,
                "patience": self.patience,
                "workers": self.workers,
                "optimizer": self.optimizer,
                "advanced_options": dict(self.advanced_options),
            }
        )


@dataclass(frozen=True, slots=True)
class DetectionSettings:
    confidence: float = DEFAULT_CONFIDENCE
    iou_threshold: float = DEFAULT_IOU_THRESH


@dataclass(frozen=True, slots=True)
class ValidationSettings:
    model_path: str = ""
    dataset_yaml: str = ""


@dataclass(frozen=True, slots=True)
class DatasetSettings:
    auto_annotation_enabled: bool = False
    last_dataset_dir: str = str(Path(PROJECT_ROOT) / "dataset")


@dataclass(frozen=True, slots=True)
class IntegrationsSettings:
    config_path: str = str(Path(PROJECT_ROOT) / "integrations_config.json")


@dataclass(frozen=True, slots=True)
class UISettings:
    theme_name: str = "dark"


@dataclass(frozen=True, slots=True)
class AppSettings:
    training: TrainingSettings
    detection: DetectionSettings
    validation: ValidationSettings
    dataset: DatasetSettings
    integrations: IntegrationsSettings
    ui: UISettings

    @classmethod
    def default(cls) -> "AppSettings":
        return cls(
            training=TrainingSettings.default(),
            detection=DetectionSettings(),
            validation=ValidationSettings(),
            dataset=DatasetSettings(),
            integrations=IntegrationsSettings(),
            ui=UISettings(),
        )
