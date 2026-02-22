"""
Domain for Hyperparameter Tuning (model.tune).

Ref: https://docs.ultralytics.com/ru/guides/hyperparameter-tuning/
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TuningConfig:
    enabled: bool = False
    data_yaml: str = ""
    model_path: str = ""
    epochs: int = 30
    iterations: int = 300
    project: str = "runs/detect"
    name: str = "tune"

    def to_dict(self) -> dict[str, Any]:
        return {
            "data_yaml": self.data_yaml,
            "model_path": self.model_path,
            "epochs": self.epochs,
            "iterations": self.iterations,
            "project": self.project,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> TuningConfig:
        if not d:
            return cls()
        return cls(
            data_yaml=str(d.get("data_yaml", "")),
            model_path=str(d.get("model_path", "")),
            epochs=int(d.get("epochs", 30)),
            iterations=int(d.get("iterations", 300)),
            project=str(d.get("project", "runs/detect")),
            name=str(d.get("name", "tune")),
        )
