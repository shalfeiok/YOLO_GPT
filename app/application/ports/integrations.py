"""Application port for Integrations configuration.

UI should depend on this port, not on feature repositories or services directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.features.comet_integration.domain import CometConfig
from app.features.dvc_integration.domain import DVCConfig
from app.features.hyperparameter_tuning.domain import TuningConfig
from app.features.kfold_integration.domain import KFoldConfig
from app.features.model_export.domain import EXPORT_FORMATS, ModelExportConfig
from app.features.model_validation.domain import ModelValidationConfig
from app.features.sagemaker_integration.domain import SageMakerConfig
from app.features.sahi_integration.domain import SahiConfig
from app.features.segmentation_isolation.domain import SegIsolationConfig


@dataclass(frozen=True)
class JobsPolicyConfig:
    default_timeout_sec: int = 0
    retries: int = 0
    retry_backoff_sec: float = 0.0
    retry_jitter: float = 0.3
    retry_deadline_sec: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> JobsPolicyConfig:
        return cls(
            default_timeout_sec=int(d.get("default_timeout_sec", 0)),
            retries=int(d.get("retries", 0)),
            retry_backoff_sec=float(d.get("retry_backoff_sec", 0.0)),
            retry_jitter=float(d.get("retry_jitter", 0.3)),
            retry_deadline_sec=int(d.get("retry_deadline_sec", 0)),
        )

    def to_dict(self) -> dict:
        return {
            "default_timeout_sec": int(self.default_timeout_sec),
            "retries": int(self.retries),
            "retry_backoff_sec": float(self.retry_backoff_sec),
            "retry_jitter": float(self.retry_jitter),
            "retry_deadline_sec": int(self.retry_deadline_sec),
        }


@dataclass(frozen=True)
class IntegrationsState:
    comet: CometConfig
    dvc: DVCConfig
    sagemaker: SageMakerConfig
    sahi: SahiConfig
    seg_isolation: SegIsolationConfig
    kfold: KFoldConfig
    tuning: TuningConfig
    model_export: ModelExportConfig
    model_validation: ModelValidationConfig

    # Backward-compatible alias: UI historically used `state.export`.
    @property
    def export(self) -> ModelExportConfig:  # noqa: D401
        """Alias for model_export (kept for UI compatibility)."""
        return self.model_export


class IntegrationsPort(Protocol):
    @property
    def export_formats(self) -> list[str]: ...

    def load_state(self) -> IntegrationsState: ...

    def save_state(self, state: IntegrationsState) -> None: ...

    def load_jobs_policy(self) -> JobsPolicyConfig: ...

    def save_jobs_policy(self, policy: JobsPolicyConfig) -> None: ...


__all__ = [
    "EXPORT_FORMATS",
    "JobsPolicyConfig",
    "IntegrationsState",
    "IntegrationsPort",
]
