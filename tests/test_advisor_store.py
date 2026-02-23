from app.application.advisor_state import AdvisorStore
from app.core.training_advisor.models import AdvisorReport
from app.domain.training_config import TrainingConfig


def _sample_report() -> AdvisorReport:
    cfg = TrainingConfig.from_current_state({})
    return AdvisorReport(
        dataset_health={},
        run_summary={},
        model_eval={},
        recommendations=[],
        recommended_training_config=cfg,
        diff=[],
        warnings=[],
        errors=[],
    )


def test_advisor_store_notifies_subscribers_on_update() -> None:
    store = AdvisorStore()
    updates = []
    unsubscribe = store.subscribe(lambda state: updates.append(state))

    store.update(
        report=_sample_report(),
        model_weights="/tmp/model.pt",
        dataset="/tmp/ds",
        run_folder=None,
    )

    assert len(updates) == 1
    assert updates[0].recommended_training_config is not None

    unsubscribe()
    store.update(
        report=_sample_report(),
        model_weights="/tmp/model.pt",
        dataset="/tmp/ds",
        run_folder=None,
    )
    assert len(updates) == 1
