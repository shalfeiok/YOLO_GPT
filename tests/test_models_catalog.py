from app.models import YOLO_MODEL_CHOICES


def test_yolo26_models_present_in_catalog() -> None:
    model_ids = {choice.model_id for choice in YOLO_MODEL_CHOICES}
    assert {"yolo26n.pt", "yolo26s.pt", "yolo26m.pt", "yolo26l.pt", "yolo26x.pt"}.issubset(
        model_ids
    )
