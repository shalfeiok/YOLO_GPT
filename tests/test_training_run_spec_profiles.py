from __future__ import annotations

from pathlib import Path

from app.application.use_cases.train_model import (
    TrainingProfile,
    TrainModelRequest,
    build_training_run_spec,
)


def _request() -> TrainModelRequest:
    return TrainModelRequest(
        data_yaml=Path("/tmp/data.yaml"),
        model_name="yolo11n.pt",
        epochs=10,
        batch=8,
        imgsz=640,
        device="cpu",
        patience=5,
        project=Path("/tmp/runs"),
        weights_path=None,
        workers=6,
        optimizer="auto",
        advanced_options={"cache": False, "seed": 0},
    )


def test_training_run_spec_is_json_serializable_dict_shape() -> None:
    spec = build_training_run_spec(_request())

    data = spec.to_dict()
    assert data["model_name"] == "yolo11n.pt"
    assert data["project"] == "/tmp/runs"
    assert data["output_dir"] == "/tmp/runs"
    assert isinstance(data["advanced_options"], dict)


def test_deterministic_profile_adjusts_workers_seed_and_cache() -> None:
    spec = build_training_run_spec(_request(), profile=TrainingProfile.DETERMINISTIC)

    assert spec.deterministic is True
    assert spec.seed == 42
    assert spec.workers <= 2
    assert spec.cache == "disk"
    assert spec.advanced_options["deterministic"] is True


def test_fast_local_profile_enables_speed_focused_defaults() -> None:
    spec = build_training_run_spec(_request(), profile=TrainingProfile.FAST_LOCAL)

    assert spec.deterministic is False
    assert spec.workers >= 4
    assert spec.cache is True
