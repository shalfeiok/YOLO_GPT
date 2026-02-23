from pathlib import Path

from app.application.use_cases.export_model import ExportModelUseCase
from app.application.use_cases.start_detection import (
    StartDetectionRequest,
    StartDetectionUseCase,
)
from app.application.use_cases.stop_detection import StopDetectionRequest, StopDetectionUseCase
from app.application.use_cases.validate_model import ValidateModelUseCase


class _Exporter:
    def export(self, config):
        return Path("/tmp/model.onnx")


class _Validator:
    def validate(self, config, *, on_progress=None):
        if on_progress:
            on_progress(1.0, "done")
        return {"metrics": {"map50": 0.42}}


class _Detector:
    def __init__(self):
        self.loaded = None
        self.unloaded = False

    def load_model(self, path: Path) -> None:
        self.loaded = path

    def is_exporting(self) -> bool:
        return False

    def unload_model(self) -> None:
        self.unloaded = True


class _DetectionPort:
    def __init__(self):
        self.detector = _Detector()

    def get_for_visualization_backend(self, backend_id: str):
        assert backend_id == "opencv"
        return self.detector


def test_export_and_validate_use_cases_smoke() -> None:
    export_uc = ExportModelUseCase(_Exporter())
    validate_uc = ValidateModelUseCase(_Validator())

    assert export_uc.execute(config=object()) == Path("/tmp/model.onnx")
    out = validate_uc.execute(config=object())
    assert out["metrics"]["map50"] == 0.42


def test_start_and_stop_detection_use_cases(tmp_path: Path) -> None:
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"x")

    port = _DetectionPort()
    start_uc = StartDetectionUseCase(port)
    result = start_uc.execute(
        StartDetectionRequest(
            weights_path=weights,
            confidence_text="0.25",
            iou_text="0.45",
            backend_id="opencv",
        )
    )
    assert result.confidence == 0.25
    assert port.detector.loaded == weights

    StopDetectionUseCase().execute(StopDetectionRequest(detector=port.detector, release_cuda_cache=False))
    assert port.detector.unloaded is True
