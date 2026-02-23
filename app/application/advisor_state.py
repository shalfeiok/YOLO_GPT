from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable
from typing import Protocol

from app.core.training_advisor.models import AdvisorReport
from app.domain.training_config import TrainingConfig


@dataclass(slots=True)
class AdvisorState:
    report: AdvisorReport | None = None
    recommended_training_config: TrainingConfig | None = None
    created_at: datetime | None = None
    model_weights_path: str | None = None
    dataset_path: str | None = None
    run_folder_path: str | None = None


class TrainingConfigTarget(Protocol):
    def get_current_training_state(self) -> dict: ...

    def apply_training_state(self, state: dict) -> None: ...


class AdvisorStore:
    def __init__(self) -> None:
        self._state = AdvisorState()
        self._subscribers: list[Callable[[AdvisorState], None]] = []

    @property
    def state(self) -> AdvisorState:
        return self._state

    def update(self, *, report: AdvisorReport, model_weights: str, dataset: str, run_folder: str | None) -> None:
        self._state = AdvisorState(
            report=report,
            recommended_training_config=report.recommended_training_config,
            created_at=datetime.now(),
            model_weights_path=model_weights,
            dataset_path=dataset,
            run_folder_path=run_folder,
        )
        for callback in list(self._subscribers):
            callback(self._state)

    def subscribe(self, callback: Callable[[AdvisorState], None]) -> Callable[[], None]:
        self._subscribers.append(callback)

        def _unsubscribe() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        return _unsubscribe
