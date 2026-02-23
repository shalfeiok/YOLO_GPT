from app.application.use_cases.training_advisor import ApplyAdvisorRecommendationsUseCase
from app.domain.training_config import TrainingConfig


class _Target:
    def __init__(self) -> None:
        self.state = {
            "model_name": "yolo11n.pt",
            "dataset_paths": ["dataset"],
            "project": "runs/train",
            "epochs": 50,
            "batch": 16,
            "imgsz": 640,
            "patience": 20,
            "workers": 2,
            "optimizer": "",
            "advanced_options": {},
        }

    def get_current_training_state(self):
        return self.state

    def apply_training_state(self, state):
        self.state = state


def test_apply_and_undo() -> None:
    target = _Target()
    uc = ApplyAdvisorRecommendationsUseCase()
    rec = TrainingConfig.from_current_state({**target.state, "epochs": 100, "batch": 8})
    diff = uc.execute(rec, target)
    assert any(d["param"] == "epochs" for d in diff)
    undo_diff = uc.undo(target)
    assert any(d["param"] == "epochs" for d in undo_diff)
    assert target.state["epochs"] == 50
