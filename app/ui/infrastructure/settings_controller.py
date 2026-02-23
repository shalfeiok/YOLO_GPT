from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.application.settings.models import AppSettings, TrainingSettings
from app.application.settings.store import AppSettingsStore


class SettingsController:
    """UI adapter over AppSettingsStore.

    Keeps UI from touching store internals and offers domain-specific operations.
    """

    def __init__(self, store: AppSettingsStore) -> None:
        self._store = store

    def snapshot(self) -> AppSettings:
        return self._store.get_snapshot()

    def training(self) -> TrainingSettings:
        return self.snapshot().training

    def update_training(self, **changes: Any) -> TrainingSettings:
        return self._store.update_training(**changes)

    def subscribe_training(self, callback: Callable[[TrainingSettings], None]) -> Callable[[], None]:
        def _cb(_topic: str, payload: Any) -> None:
            callback(payload)

        return self._store.subscribe("training_changed", _cb)
