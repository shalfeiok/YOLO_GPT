"""
Domain model for K-Fold Cross Validation (Ultralytics guide).

Ref: https://docs.ultralytics.com/ru/guides/kfold-cross-validation/
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


@dataclass
class KFoldConfig:
    """Parameters for K-Fold dataset split and optional training."""

    enabled: bool = False
    dataset_path: str = ""
    data_yaml_path: str = ""
    k_folds: int = 5
    random_state: int = 20
    output_path: str = ""
    # Optional: train after split
    weights_path: str = ""
    train_epochs: int = 100
    train_batch: int = 16
    train_project: str = "kfold_demo"

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "dataset_path": self.dataset_path,
            "data_yaml_path": self.data_yaml_path,
            "k_folds": self.k_folds,
            "random_state": self.random_state,
            "output_path": self.output_path,
            "weights_path": self.weights_path,
            "train_epochs": self.train_epochs,
            "train_batch": self.train_batch,
            "train_project": self.train_project,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> KFoldConfig:
        if not d:
            return cls()
        return cls(
            enabled=_as_bool(d.get("enabled"), False),
            dataset_path=str(d.get("dataset_path", "")),
            data_yaml_path=str(d.get("data_yaml_path", "")),
            k_folds=int(d.get("k_folds", 5)),
            random_state=int(d.get("random_state", 20)),
            output_path=str(d.get("output_path", "")),
            weights_path=str(d.get("weights_path", "")),
            train_epochs=int(d.get("train_epochs", 100)),
            train_batch=int(d.get("train_batch", 16)),
            train_project=str(d.get("train_project", "kfold_demo")),
        )

    @property
    def k(self) -> int:
        return int(self.k_folds)

    @k.setter
    def k(self, value: int) -> None:
        self.k_folds = int(value)

