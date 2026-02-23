from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from threading import RLock
from typing import Any

from .models import AppSettings, DetectionSettings, TrainingSettings

Subscriber = Callable[[str, Any], None]


class AppSettingsStore:
    def __init__(self, initial: AppSettings | None = None) -> None:
        self._defaults = initial or AppSettings.default()
        self._state = self._defaults
        self._lock = RLock()
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)

    def get_snapshot(self) -> AppSettings:
        with self._lock:
            return deepcopy(self._state)

    def subscribe(self, topic: str, callback: Subscriber) -> Callable[[], None]:
        with self._lock:
            self._subscribers[topic].append(callback)

        def _unsubscribe() -> None:
            with self._lock:
                if callback in self._subscribers.get(topic, []):
                    self._subscribers[topic].remove(callback)

        return _unsubscribe

    def reset_to_defaults(self) -> None:
        with self._lock:
            self._state = deepcopy(self._defaults)
        self._emit("settings_changed", self.get_snapshot())

    def update_training(self, **changes: Any) -> TrainingSettings:
        with self._lock:
            training = replace(self._state.training, **changes)
            self._validate_training(training)
            self._state = replace(self._state, training=training)
        self._emit("training_changed", training)
        self._emit("settings_changed", self.get_snapshot())
        return training

    def update_detection(self, **changes: Any) -> DetectionSettings:
        with self._lock:
            detection = replace(self._state.detection, **changes)
            self._state = replace(self._state, detection=detection)
        self._emit("detection_changed", detection)
        self._emit("settings_changed", self.get_snapshot())
        return detection

    def _validate_training(self, training: TrainingSettings) -> None:
        if training.epochs < 1:
            raise ValueError("epochs must be >= 1")
        if training.batch < -1:
            raise ValueError("batch must be >= -1")
        if not (64 <= training.imgsz <= 2048):
            raise ValueError("imgsz must be in [64, 2048]")
        if training.patience < 1:
            raise ValueError("patience must be >= 1")
        if training.workers < 0:
            raise ValueError("workers must be >= 0")

    def _emit(self, topic: str, payload: Any) -> None:
        with self._lock:
            callbacks = list(self._subscribers.get(topic, [])) + list(
                self._subscribers.get("*", [])
            )
        for callback in callbacks:
            callback(topic, payload)
