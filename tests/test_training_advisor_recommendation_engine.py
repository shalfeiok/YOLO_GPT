from app.core.training_advisor.recommendation_engine import RecommendationEngine
from app.domain.training_config import TrainingConfig


def _cfg() -> TrainingConfig:
    return TrainingConfig.from_current_state(
        {
            "model_name": "yolo11n.pt",
            "dataset_paths": ["dataset"],
            "project": "runs/train",
            "epochs": 50,
            "batch": 16,
            "imgsz": 640,
            "patience": 20,
            "workers": 1,
            "optimizer": "",
            "advanced_options": {},
        }
    )


def test_recommendation_engine_imbalance_and_errors() -> None:
    cfg, items, diff, _ = RecommendationEngine().recommend(
        _cfg(),
        {"errors": ["bad labels"], "warnings": ["class imbalance detected (>5x)"], "statistics": {}},
        {"metrics": {"metrics/mAP50(B)": "0.5", "train/box_loss": "0.3"}},
        {"metrics": {}},
    )
    assert cfg.advanced_options["mosaic"] == 1.0
    assert any(i.param == "advanced_options.mixup" for i in items)
    assert any(d["param"].startswith("advanced_options") for d in diff)


def test_recommendation_engine_underfitting() -> None:
    cfg, _, _, _ = RecommendationEngine().recommend(
        _cfg(),
        {"errors": [], "warnings": [], "statistics": {}},
        {"metrics": {"metrics/mAP50(B)": "0.1", "train/box_loss": "0.8"}},
        {"metrics": {"map50": 0.05}},
    )
    assert cfg.epochs >= 120
    assert cfg.patience >= 40
