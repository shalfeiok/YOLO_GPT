"""ONNX detection service: IDetector implementation delegating to ONNXBackend."""
from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, Tuple

import numpy as np

from app.interfaces import IDetector
from app.yolo_inference.backends.onnx_backend import ONNXBackend


class OnnxDetectionService(IDetector):
    """Detection via ONNX Runtime; inference delegated to ONNXBackend."""

    def __init__(self) -> None:
        self._backend = ONNXBackend()

    def load_model(self, weights_path: Path) -> None:
        self._backend.load(weights_path)

    def ensure_model_ready(self) -> None:
        """No-op for ONNX; model is loaded in load_model() or via async export."""
        pass

    def predict(
        self,
        frame: np.ndarray,
        conf: float = 0.45,
        iou: float = 0.45,
    ) -> Tuple[np.ndarray, List[Any]]:
        return self._backend.predict(frame, conf=conf, iou=iou)

    def is_exporting(self) -> bool:
        """Part 3: True while .pt is being exported to .onnx asynchronously."""
        return self._backend.is_exporting()

    def get_export_error(self) -> Optional[str]:
        return self._backend.get_export_error()

    def unload_model(self) -> None:
        """Part 5.8: Release session on detection stop."""
        self._backend.unload_model()

    @property
    def is_loaded(self) -> bool:
        return self._backend.is_loaded
