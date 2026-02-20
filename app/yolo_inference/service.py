"""YOLO detection service: IDetector implementation delegating to PyTorchBackend."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from app.interfaces import IDetector
from app.yolo_inference.backends.pytorch_backend import PyTorchBackend


class DetectionService(IDetector):
    """Detection via Ultralytics YOLO; inference delegated to PyTorchBackend."""

    def __init__(self) -> None:
        self._backend = PyTorchBackend()

    def load_model(self, weights_path: Path) -> None:
        self._backend.load(weights_path)

    def ensure_model_ready(self) -> None:
        """Part 1: Create model in current thread (inference thread) and pre-warm. No-op if already created."""
        self._backend.ensure_model_created_in_current_thread()

    def predict(
        self,
        frame: np.ndarray,
        conf: float = 0.45,
        iou: float = 0.45,
    ) -> tuple[np.ndarray, list[Any]]:
        return self._backend.predict(frame, conf=conf, iou=iou)

    def unload_model(self) -> None:
        """Part 5.8: Release model and GPU cache on detection stop."""
        self._backend.unload_model()

    @property
    def is_loaded(self) -> bool:
        return self._backend.is_loaded
