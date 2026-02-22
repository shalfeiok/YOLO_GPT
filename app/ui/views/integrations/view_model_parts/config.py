from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from app.application.ports.integrations import (
    CometConfig,
    DVCConfig,
    IntegrationsState,
    KFoldConfig,
    ModelExportConfig,
    ModelValidationConfig,
    SageMakerConfig,
    SegIsolationConfig,
    SahiConfig,
    TuningConfig,
)
from app.application.use_cases.integrations_config import (
    DefaultIntegrationsConfigRepository,
    ExportIntegrationsConfigRequest,
    ExportIntegrationsConfigUseCase,
    ImportIntegrationsConfigRequest,
    ImportIntegrationsConfigUseCase,
)


class IntegrationsConfigMixin:
    def _policy_kwargs(
        self,
        *,
        min_timeout_sec: int = 0,
        min_retries: int = 0,
        min_backoff_sec: float = 0.0,
    ) -> dict[str, Any]:
        p = self.integrations.load_jobs_policy()
        timeout = max(int(p.default_timeout_sec), int(min_timeout_sec))
        retries = max(int(p.retries), int(min_retries))
        backoff = max(float(p.retry_backoff_sec), float(min_backoff_sec))
        return {
            "timeout_sec": timeout if timeout > 0 else None,
            "retries": retries,
            "retry_backoff_sec": backoff,
            "retry_jitter": float(p.retry_jitter),
            "retry_deadline_sec": int(p.retry_deadline_sec) if int(p.retry_deadline_sec) > 0 else None,
        }

    def load_state(self) -> IntegrationsState:
        return self.integrations.load_state()

    def refresh_state(self) -> IntegrationsState:
        state = self.load_state()
        self.state_changed.emit(state)
        return state

    def export_integrations_config(self, path: Path) -> None:
        uc = self._container.export_integrations_config_use_case if self._container else ExportIntegrationsConfigUseCase(DefaultIntegrationsConfigRepository())
        uc.execute(ExportIntegrationsConfigRequest(path=path))

    def import_integrations_config(self, path: Path) -> None:
        uc = self._container.import_integrations_config_use_case if self._container else ImportIntegrationsConfigUseCase(DefaultIntegrationsConfigRepository())
        uc.execute(ImportIntegrationsConfigRequest(path=path))
        self.refresh_state()

    def _update_state(self, **changes: Any) -> IntegrationsState:
        state = self.load_state()
        new_state = replace(state, **changes)
        self.integrations.save_state(new_state)
        self.refresh_state()
        return new_state

    def save_comet(self, cfg: CometConfig) -> None: self._update_state(comet=cfg)
    def save_dvc(self, cfg: DVCConfig) -> None: self._update_state(dvc=cfg)
    def save_sagemaker(self, cfg: SageMakerConfig) -> None: self._update_state(sagemaker=cfg)
    def save_kfold(self, cfg: KFoldConfig) -> None: self._update_state(kfold=cfg)
    def save_tuning(self, cfg: TuningConfig) -> None: self._update_state(tuning=cfg)
    def save_export(self, cfg: ModelExportConfig) -> None: self._update_state(model_export=cfg)
    def save_sahi(self, cfg: SahiConfig) -> None: self._update_state(sahi=cfg)
    def save_seg_isolation(self, cfg: SegIsolationConfig) -> None: self._update_state(seg_isolation=cfg)
    def save_validation(self, cfg: ModelValidationConfig) -> None: self._update_state(model_validation=cfg)

    def reset_comet(self) -> CometConfig:
        cfg = CometConfig(enabled=False, api_key="", project_name="yolo26-project", max_image_predictions=100, eval_batch_logging_interval=1, eval_log_confusion_matrix=True, mode="online")
        self._update_state(comet=cfg)
        return cfg

    def reset_dvc(self) -> DVCConfig:
        cfg = DVCConfig(enabled=False)
        self._update_state(dvc=cfg)
        return cfg

    def reset_sagemaker(self) -> SageMakerConfig:
        cfg = SageMakerConfig(instance_type="ml.m5.4xlarge", endpoint_name="", model_path="", template_cloned_path="")
        self._update_state(sagemaker=cfg)
        return cfg

    def reset_kfold(self) -> KFoldConfig:
        cfg = KFoldConfig()
        self._update_state(kfold=cfg)
        return cfg

    def reset_tuning(self) -> TuningConfig:
        cfg = TuningConfig()
        self._update_state(tuning=cfg)
        return cfg

    def reset_export(self) -> ModelExportConfig:
        cfg = ModelExportConfig()
        self._update_state(model_export=cfg)
        return cfg

    def reset_sahi(self) -> SahiConfig:
        cfg = SahiConfig()
        self._update_state(sahi=cfg)
        return cfg

    def save_seg(self, cfg: SegIsolationConfig) -> None:
        self.save_seg_isolation(cfg)

    def reset_seg(self) -> SegIsolationConfig:
        cfg = SegIsolationConfig()
        self._update_state(seg_isolation=cfg)
        return cfg

    def reset_validation(self) -> ModelValidationConfig:
        cfg = ModelValidationConfig()
        self._update_state(model_validation=cfg)
        return cfg
