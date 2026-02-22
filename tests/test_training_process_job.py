from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from app.application.jobs.risky_job_fns import train_model_job
from app.core.errors import CancelledError


class _CancelEvt:
    def __init__(self, cancelled: bool = False) -> None:
        self._cancelled = cancelled

    def is_set(self) -> bool:
        return self._cancelled


def test_train_model_job_rejects_pre_cancelled() -> None:
    with pytest.raises(CancelledError):
        train_model_job(_CancelEvt(cancelled=True), lambda *_: None, cfg={})


def test_train_model_job_uses_training_service(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}

    class _FakeTrainingService:
        def stop(self) -> None:
            calls["stopped"] = True

        def train(self, **kwargs):
            calls["kwargs"] = kwargs
            kwargs["on_progress"](0.5, "half")
            return tmp_path / "best.pt"

    fake_mod = types.ModuleType("app.services.training_service")
    fake_mod.TrainingService = _FakeTrainingService
    monkeypatch.setitem(sys.modules, "app.services.training_service", fake_mod)

    progress: list[tuple[float, str | None]] = []
    result = train_model_job(
        _CancelEvt(cancelled=False),
        lambda p, m=None: progress.append((p, m)),
        cfg={
            "data_yaml": str(tmp_path / "data.yaml"),
            "model_name": "yolov8n.pt",
            "epochs": 1,
            "batch": 4,
            "imgsz": 640,
            "device": "cpu",
            "patience": 5,
            "project": str(tmp_path / "runs"),
            "weights_path": None,
            "workers": 2,
            "optimizer": "SGD",
            "advanced_options": {"cache": "disk"},
        },
    )

    assert result == str(tmp_path / "best.pt")
    assert progress == [(0.5, "half")]
    kwargs = calls["kwargs"]
    assert kwargs["workers"] == 2
    assert kwargs["advanced_options"]["cache"] == "disk"
