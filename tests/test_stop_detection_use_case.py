from __future__ import annotations

import pytest

from app.application.use_cases.stop_detection import (
    StopDetectionError,
    StopDetectionRequest,
    StopDetectionUseCase,
)


class DummyDetector:
    def __init__(self) -> None:
        self.unloaded = False

    def unload_model(self) -> None:
        self.unloaded = True


class FailingDetector:
    def unload_model(self) -> None:
        raise RuntimeError("boom")


def test_stop_detection_unloads_model() -> None:
    uc = StopDetectionUseCase()
    det = DummyDetector()
    uc.execute(StopDetectionRequest(detector=det, release_cuda_cache=False))
    assert det.unloaded is True


def test_stop_detection_is_idempotent_with_none_detector() -> None:
    uc = StopDetectionUseCase()
    uc.execute(StopDetectionRequest(detector=None, release_cuda_cache=False))


def test_stop_detection_wraps_unload_error() -> None:
    uc = StopDetectionUseCase()
    with pytest.raises(StopDetectionError):
        uc.execute(StopDetectionRequest(detector=FailingDetector(), release_cuda_cache=False))
