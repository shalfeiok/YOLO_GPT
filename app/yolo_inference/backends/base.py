"""Abstract model backend for detection inference (Part 4.10). IDetector is unchanged; services delegate here."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np


class AbstractModelBackend(ABC):
    """Internal inference backend. DetectionService/OnnxDetectionService delegate to a backend."""

    @abstractmethod
    def load(self, weights_path: Path) -> None:
        """Load model from weights path."""
        ...

    @abstractmethod
    def predict(
        self,
        frame: np.ndarray,
        conf: float = 0.45,
        iou: float = 0.45,
    ) -> tuple[np.ndarray, list[Any]]:
        """Run detection. Returns (annotated_frame, results)."""
        ...

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Whether the model is loaded."""
        ...
