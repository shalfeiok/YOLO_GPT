from app.application.settings.diff import settings_diff
from app.domain.training_config import TrainingConfig, diff_training_config


def test_training_config_validate_and_diff() -> None:
    bad = TrainingConfig.from_current_state({"epochs": 0, "imgsz": 32, "patience": 0, "workers": 99})
    errors = bad.validate()
    assert any("epochs" in e for e in errors)
    assert any("imgsz" in e for e in errors)

    current = TrainingConfig.from_current_state({"epochs": 50, "batch": 16, "advanced_options": {"mixup": 0.0}})
    recommended = TrainingConfig.from_current_state({"epochs": 120, "batch": 8, "advanced_options": {"mixup": 0.2}})
    diff = diff_training_config(current, recommended)
    assert any(d["param"] == "epochs" for d in diff)
    assert any(d["param"] == "advanced_options.mixup" for d in diff)


def test_settings_diff_flatten_nested_dict() -> None:
    current = {"training": {"epochs": 50, "advanced_options": {"mixup": 0.0}}}
    updated = {"training": {"epochs": 100, "advanced_options": {"mixup": 0.15}}}
    diff = settings_diff(current, updated)
    params = {x["param"] for x in diff}
    assert "training.epochs" in params
    assert "training.advanced_options.mixup" in params
