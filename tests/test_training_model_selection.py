from pathlib import Path

from app.ui.views.training.model_selection import (
    CUSTOM_MODEL_CHOICE,
    resolve_model_choice_label,
)


def test_resolve_base_model_choice_label() -> None:
    label = resolve_model_choice_label(
        model_name="yolo11s.pt",
        weights_path=None,
        trained_choices=[("best-1", Path("/tmp/runs/train1/weights/best.pt"))],
        base_choices=[("YOLO11n", "yolo11n.pt"), ("YOLO11s", "yolo11s.pt")],
    )
    assert label == "YOLO11s"


def test_resolve_trained_choice_from_weights_path() -> None:
    label = resolve_model_choice_label(
        model_name="yolo11n.pt",
        weights_path="/tmp/runs/train42/weights/best.pt",
        trained_choices=[("Последняя лучшая", Path("/tmp/runs/train42/weights/best.pt"))],
        base_choices=[("YOLO11n", "yolo11n.pt")],
    )
    assert label == "Последняя лучшая"


def test_resolve_custom_choice_when_weights_not_in_trained_list() -> None:
    label = resolve_model_choice_label(
        model_name="yolo11n.pt",
        weights_path="/tmp/custom/model.pt",
        trained_choices=[],
        base_choices=[("YOLO11n", "yolo11n.pt")],
    )
    assert label == CUSTOM_MODEL_CHOICE
