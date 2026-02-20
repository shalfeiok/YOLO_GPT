"""
Domain models for Comet ML integration.

Ref: https://docs.ultralytics.com/ru/integrations/comet/
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class CometConfig:
    """Config for Comet ML experiment logging."""

    enabled: bool
    api_key: str
    project_name: str
    max_image_predictions: int
    eval_batch_logging_interval: int
    eval_log_confusion_matrix: bool
    mode: str  # online, offline, disabled

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CometConfig":
        return cls(
            enabled=bool(d.get("enabled", False)),
            api_key=str(d.get("api_key", "")),
            project_name=str(d.get("project_name", "yolo26-project")),
            max_image_predictions=int(d.get("max_image_predictions", 100)),
            eval_batch_logging_interval=int(d.get("eval_batch_logging_interval", 1)),
            eval_log_confusion_matrix=bool(d.get("eval_log_confusion_matrix", True)),
            mode=str(d.get("mode", "online")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "api_key": self.api_key,
            "project_name": self.project_name,
            "max_image_predictions": self.max_image_predictions,
            "eval_batch_logging_interval": self.eval_batch_logging_interval,
            "eval_log_confusion_matrix": self.eval_log_confusion_matrix,
            "mode": self.mode,
        }
