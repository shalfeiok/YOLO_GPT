"""Infra adapter implementing IntegrationsPort using feature repositories."""
from __future__ import annotations

import logging

from app.application.ports.integrations import IntegrationsPort, IntegrationsState, JobsPolicyConfig
from app.features.integrations_config import load_config, save_config

from app.features.comet_integration.repository import load_comet_config, save_comet_config
from app.features.dvc_integration.repository import load_dvc_config, save_dvc_config
from app.features.hyperparameter_tuning.repository import load_tuning_config, save_tuning_config
from app.features.kfold_integration.repository import load_kfold_config, save_kfold_config
from app.features.model_export.repository import load_export_config, save_export_config
from app.features.model_validation.repository import load_validation_config, save_validation_config
from app.features.sagemaker_integration.repository import load_sagemaker_config, save_sagemaker_config
from app.features.sahi_integration.repository import load_sahi_config, save_sahi_config
from app.features.segmentation_isolation.repository import load_seg_isolation_config, save_seg_isolation_config

from app.features.model_export.domain import EXPORT_FORMATS

log = logging.getLogger(__name__)


class IntegrationsAdapter(IntegrationsPort):
    """Single entry point for integrations configs and jobs policy."""

    @property
    def export_formats(self) -> list[str]:
        return list(EXPORT_FORMATS)

    def load_state(self) -> IntegrationsState:
        return IntegrationsState(
            comet=load_comet_config(),
            dvc=load_dvc_config(),
            sagemaker=load_sagemaker_config(),
            sahi=load_sahi_config(),
            seg_isolation=load_seg_isolation_config(),
            kfold=load_kfold_config(),
            tuning=load_tuning_config(),
            model_export=load_export_config(),
            model_validation=load_validation_config(),
        )

    def save_state(self, state: IntegrationsState) -> None:
        # Save via feature repositories so each section writes to the same integrations config file.
        save_comet_config(state.comet)
        save_dvc_config(state.dvc)
        save_sagemaker_config(state.sagemaker)
        save_sahi_config(state.sahi)
        save_seg_isolation_config(state.seg_isolation)
        save_kfold_config(state.kfold)
        save_tuning_config(state.tuning)
        save_export_config(state.model_export)
        save_validation_config(state.model_validation)

    def load_jobs_policy(self) -> JobsPolicyConfig:
        cfg = load_config()
        raw = cfg.get("jobs_policy", {}) if isinstance(cfg, dict) else {}
        try:
            return JobsPolicyConfig.from_dict(raw if isinstance(raw, dict) else {})
        except Exception:
            log.debug("Failed to parse jobs_policy from integrations config", exc_info=True)
            return JobsPolicyConfig()

    def save_jobs_policy(self, policy: JobsPolicyConfig) -> None:
        cfg = load_config()
        if not isinstance(cfg, dict):
            cfg = {}
        cfg["jobs_policy"] = policy.to_dict()
        save_config(cfg)
