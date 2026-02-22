"""Абстрактные интерфейсы (SOLID: Dependency Inversion).

Определяет контракты для обучения (ITrainer), детекции (IDetector),
захвата окна/экрана (IWindowCapture) и сборки конфига датасета (IDatasetConfigBuilder).
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import numpy as np


class ITrainer(Protocol):
    """Интерфейс обучения YOLO: запуск обучения и остановка по запросу."""

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
        on_progress: Callable[[float, str], None] | None = None,
        console_queue: Any = None,
        weights_path: Path | None = None,
        workers: int = 0,
        optimizer: str = "",
        advanced_options: dict[str, Any] | None = None,
    ) -> Path | None:
        """Run training. Returns path to best weights. If weights_path is set, load from it instead of model_name."""
        ...

    def stop(self) -> None:
        """Request stop of current training."""
        ...


class IDetector(ABC):
    """Интерфейс инференса детекции: загрузка модели и предсказание по кадру."""

    @abstractmethod
    def load_model(self, weights_path: Path) -> None:
        """Load model from weights file."""
        ...

    @abstractmethod
    def predict(
        self,
        frame: np.ndarray,
        conf: float = 0.45,
        iou: float = 0.45,
    ) -> tuple[np.ndarray, list[Any]]:
        """Run detection on frame. Returns (annotated_frame, results_list)."""
        ...

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Whether model is loaded."""
        ...


class IWindowCapture(ABC):
    """Интерфейс захвата кадров: список окон, захват окна или всего экрана."""

    @abstractmethod
    def list_windows(self) -> list[tuple[int, str]]:
        """Return list of (hwnd, title) for selectable windows."""
        ...

    @abstractmethod
    def capture_window(self, hwnd: int) -> np.ndarray | None:
        """Capture frame from window by hwnd. Returns BGR numpy array or None."""
        ...

    @abstractmethod
    def capture_primary_monitor(self) -> np.ndarray | None:
        """Capture full primary monitor. Returns BGR numpy array or None."""
        ...


class IDatasetConfigBuilder(ABC):
    """Интерфейс сборки объединённого data.yaml из нескольких датасетов."""

    @abstractmethod
    def build(
        self,
        dataset1_path: Path,
        dataset2_path: Path,
        output_yaml: Path,
        primary_yaml: Path | None = None,
    ) -> Path:
        """Build combined data.yaml. Returns path to output_yaml."""
        ...
