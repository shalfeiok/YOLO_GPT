from __future__ import annotations

from app.application.ports.capture import FrameSourceSpec
from app.application.ports.detection import DetectorSpec
from app.features.detection_visualization.domain import BACKEND_ONNX, BACKEND_OPENCV
from app.services.adapters import CaptureAdapter, DetectionAdapter


def test_capture_adapter_creates_frame_source() -> None:
    cap = CaptureAdapter()
    src = cap.create_frame_source(FrameSourceSpec(source=0))
    # Protocol surface
    assert hasattr(src, "read")
    assert hasattr(src, "release")
    assert hasattr(src, "is_opened")
    assert isinstance(src.is_opened(), bool)


def test_detection_adapter_returns_cached_detectors() -> None:
    det = DetectionAdapter()
    a = det.get_detector(DetectorSpec(engine="pytorch"))
    b = det.get_detector(DetectorSpec(engine="pytorch"))
    c = det.get_detector(DetectorSpec(engine="onnx"))
    d = det.get_detector(DetectorSpec(engine="onnx"))
    assert a is b
    assert c is d
    assert a is not c


def test_detection_adapter_resolves_by_visualization_backend() -> None:
    det = DetectionAdapter()
    onnx = det.get_for_visualization_backend(BACKEND_ONNX)
    pt = det.get_for_visualization_backend(BACKEND_OPENCV)
    assert onnx is det.get_detector(DetectorSpec(engine="onnx"))
    assert pt is det.get_detector(DetectorSpec(engine="pytorch"))
