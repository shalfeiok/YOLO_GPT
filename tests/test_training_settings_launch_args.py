from pathlib import Path

from app.application.settings.store import AppSettingsStore
from app.application.use_cases.training_advisor import ApplyAdvisorRecommendationsUseCase
from app.domain.training_config import TrainingConfig
from app.ui.views.training.train_args import build_training_launch_args


def test_apply_recommendations_affects_next_training_launch_args() -> None:
    store = AppSettingsStore()
    apply_uc = ApplyAdvisorRecommendationsUseCase(store)

    current_cfg = store.get_snapshot().training.to_training_config().to_dict()
    recommended = TrainingConfig.from_current_state(
        {
            **current_cfg,
            "imgsz": 960,
            "patience": 40,
            "advanced_options": {
                **current_cfg["advanced_options"],
                "mixup": 0.15,
                "mosaic": 0.3,
                "close_mosaic": 15,
            },
        }
    )

    apply_uc.execute(recommended)

    launch_args = build_training_launch_args(
        store.get_snapshot().training,
        data_yaml=Path("/tmp/dataset/data.yaml"),
        log_path=Path("/tmp/runs/train/logs/training.log"),
    )

    assert launch_args.imgsz == 960
    assert launch_args.patience == 40
    assert launch_args.advanced_options["mixup"] == 0.15
    assert launch_args.advanced_options["mosaic"] == 0.3
    assert launch_args.advanced_options["close_mosaic"] == 15


def test_build_training_launch_args_uses_only_settings_snapshot_values() -> None:
    store = AppSettingsStore()
    store.update_training(
        model_name="yolo11s.pt",
        weights_path="/tmp/custom.pt",
        epochs=55,
        batch=6,
        imgsz=896,
        patience=33,
        workers=5,
        optimizer="AdamW",
        project="/tmp/runs/custom",
        advanced_options={"mosaic": 0.25, "mixup": 0.1, "close_mosaic": 12},
    )

    launch_args = build_training_launch_args(
        store.get_snapshot().training,
        data_yaml=Path("/tmp/data.yaml"),
        log_path=Path("/tmp/log.txt"),
    )

    kwargs = launch_args.as_view_model_kwargs()
    assert kwargs["model_name"] == "yolo11s.pt"
    assert kwargs["weights_path"] == Path("/tmp/custom.pt")
    assert kwargs["epochs"] == 55
    assert kwargs["batch"] == 6
    assert kwargs["imgsz"] == 896
    assert kwargs["patience"] == 33
    assert kwargs["workers"] == 5
    assert kwargs["optimizer"] == "AdamW"
    assert kwargs["project"] == Path("/tmp/runs/custom")
    assert kwargs["advanced_options"] == {"mosaic": 0.25, "mixup": 0.1, "close_mosaic": 12}
