"""Application façade for Integrations UI.

This module provides a single import surface for the Integrations screen.
The UI should not import feature-level repositories directly.

We intentionally keep return types as domain config objects (e.g. CometConfig)
because they act as stable data contracts.
"""

from __future__ import annotations

from app.features.comet_integration.domain import CometConfig
from app.features.comet_integration.repository import load_comet_config, save_comet_config
from app.features.dvc_integration.domain import DVCConfig
from app.features.dvc_integration.repository import load_dvc_config, save_dvc_config
from app.features.hyperparameter_tuning.domain import TuningConfig
from app.features.hyperparameter_tuning.repository import load_tuning_config, save_tuning_config
from app.features.kfold_integration.domain import KFoldConfig
from app.features.kfold_integration.repository import load_kfold_config, save_kfold_config
from app.features.model_export.domain import EXPORT_FORMATS, ModelExportConfig
from app.features.model_export.repository import load_export_config, save_export_config
from app.features.model_validation.domain import ModelValidationConfig
from app.features.model_validation.repository import load_validation_config, save_validation_config
from app.features.sagemaker_integration.domain import SageMakerConfig
from app.features.sagemaker_integration.repository import load_sagemaker_config, save_sagemaker_config
from app.features.sahi_integration.domain import SahiConfig
from app.features.sahi_integration.repository import load_sahi_config, save_sahi_config
from app.features.segmentation_isolation.domain import SegIsolationConfig
from app.features.segmentation_isolation.repository import (
    load_seg_isolation_config,
    save_seg_isolation_config,
)

from app.features.integrations_config import load_config as load_integrations_config_dict
from app.features.integrations_config import save_config as save_integrations_config_dict
from dataclasses import asdict

from app.features.integrations_schema import JobsPolicyConfig, IntegrationsConfig

__all__ = [
    # Full integrations config (dict-based)
    "load_integrations_config_dict",
    "save_integrations_config_dict",
    # Jobs policy
    "JobsPolicyConfig",
    "load_jobs_policy",
    "save_jobs_policy",
    # Comet
    "CometConfig",
    "load_comet_config",
    "save_comet_config",
    # DVC
    "DVCConfig",
    "load_dvc_config",
    "save_dvc_config",
    # SageMaker
    "SageMakerConfig",
    "load_sagemaker_config",
    "save_sagemaker_config",
    # K-Fold
    "KFoldConfig",
    "load_kfold_config",
    "save_kfold_config",
    # Tuning
    "TuningConfig",
    "load_tuning_config",
    "save_tuning_config",
    # Export
    "ModelExportConfig",
    "EXPORT_FORMATS",
    "load_export_config",
    "save_export_config",
    # SAHI
    "SahiConfig",
    "load_sahi_config",
    "save_sahi_config",
    # Seg isolation
    "SegIsolationConfig",
    "load_seg_isolation_config",
    "save_seg_isolation_config",
    # Validation
    "ModelValidationConfig",
    "load_validation_config",
    "save_validation_config",
]


def load_jobs_policy() -> JobsPolicyConfig:
    cfg = load_integrations_config_dict()
    if isinstance(cfg, dict) and "jobs" not in cfg and "jobs_policy" in cfg:
        cfg = dict(cfg)
        cfg["jobs"] = cfg.get("jobs_policy")
    return IntegrationsConfig.from_dict(cfg).jobs


def save_jobs_policy(policy: JobsPolicyConfig) -> None:
    cfg = load_integrations_config_dict()
    cfg["jobs"] = asdict(policy)
    cfg.pop("jobs_policy", None)
    save_integrations_config_dict(cfg)
