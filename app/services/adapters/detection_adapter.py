"""Infrastructure adapter implementing the DetectionPort."""

from __future__ import annotations

from app.application.ports.detection import DetectionPort, DetectorSpec, detector_spec_for_backend
from app.interfaces import IDetector
from app.services import DetectionService
from app.yolo_inference.onnx_detector import OnnxDetectionService


class DetectionAdapter(DetectionPort):
    def __init__(self) -> None:
        self._pytorch: IDetector | None = None
        self._onnx: IDetector | None = None

    def get_detector(self, spec: DetectorSpec) -> IDetector:
        engine = spec.engine.lower().strip()
        if engine == "onnx":
            if self._onnx is None:
                self._onnx = OnnxDetectionService()
            return self._onnx
        # default: pytorch
        if self._pytorch is None:
            self._pytorch = DetectionService()
        return self._pytorch

    def get_for_visualization_backend(self, backend_id: str) -> IDetector:
        return self.get_detector(detector_spec_for_backend(backend_id))
