"""Use case: start detection (validate inputs + load model).

This keeps the UI thin: parsing/validation and model loading errors are handled
here and surfaced as domain-specific exceptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.application.ports.detection import DetectionPort
from app.interfaces import IDetector


class StartDetectionError(RuntimeError):
    """Raised when detection cannot be started due to invalid input or load failure."""


@dataclass(frozen=True, slots=True)
class StartDetectionRequest:
    weights_path: Path
    confidence_text: str
    iou_text: str
    backend_id: str


@dataclass(frozen=True, slots=True)
class StartDetectionResult:
    detector: IDetector
    confidence: float
    iou: float
    backend_id: str
    is_exporting: bool


class StartDetectionUseCase:
    def __init__(self, detection: DetectionPort) -> None:
        self._detection = detection

    def execute(self, req: StartDetectionRequest) -> StartDetectionResult:
        if not req.weights_path or not req.weights_path.exists():
            raise StartDetectionError("Укажите существующий файл весов (.pt или .onnx).")

        try:
            conf = float(req.confidence_text)
            iou = float(req.iou_text)
        except ValueError as e:
            raise StartDetectionError("Confidence и IOU должны быть числами.") from e

        detector = self._detection.get_for_visualization_backend(req.backend_id)
        try:
            detector.load_model(req.weights_path)
        except Exception as e:
            raise StartDetectionError(f"Не удалось загрузить модель: {e}") from e

        is_exporting = bool(getattr(detector, "is_exporting", lambda: False)())
        return StartDetectionResult(
            detector=detector,
            confidence=conf,
            iou=iou,
            backend_id=req.backend_id,
            is_exporting=is_exporting,
        )
