from app.application.settings.store import AppSettingsStore
from app.application.use_cases.training_advisor import ApplyAdvisorRecommendationsUseCase
from app.domain.training_config import TrainingConfig


def test_apply_and_undo() -> None:
    store = AppSettingsStore()
    initial_epochs = store.get_snapshot().training.epochs
    uc = ApplyAdvisorRecommendationsUseCase(store)
    rec = TrainingConfig.from_current_state(
        {
            **store.get_snapshot().training.to_training_config().to_dict(),
            "epochs": 100,
            "batch": 8,
        }
    )
    diff = uc.execute(rec)
    assert any(d["param"] == "epochs" for d in diff)
    assert store.get_snapshot().training.epochs == 100

    undo_diff = uc.undo()
    assert any(d["param"] == "epochs" for d in undo_diff)
    assert store.get_snapshot().training.epochs == initial_epochs
