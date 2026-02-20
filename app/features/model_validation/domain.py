"""
Domain for model validation (model.val) and metrics (IoU, mAP).

Ref: https://docs.ultralytics.com/ru/guides/model-evaluation-insights/
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ModelValidationConfig:
    data_yaml: str = ""
    weights_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"data_yaml": self.data_yaml, "weights_path": self.weights_path}

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> ModelValidationConfig:
        if not d:
            return cls()
        return cls(
            data_yaml=str(d.get("data_yaml", "")),
            weights_path=str(d.get("weights_path", "")),
        )
