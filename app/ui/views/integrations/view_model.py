"""Integrations ViewModel (MVVM).

The Integrations tab is mostly configuration management + a few utility actions (export, validation,
SAHI tiled inference, segmentation isolation, K-Fold tooling).

This ViewModel keeps UI thin:
- Loads/saves/reset configs via the application facade.
- Executes actions via feature services / application use-cases.

The View owns widgets; the ViewModel owns data and side effects.
"""

from __future__ import annotations

from dataclasses import replace
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.application.jobs.risky_job_fns import (
    sagemaker_cdk_deploy_job,
    sagemaker_clone_template_job,
    sahi_predict_job,
    tune_job,
)
from app.core.errors import CancelledError
from app.core.jobs import JobHandle, ProcessJobHandle

try:  # Optional in headless test environments.
    from PySide6.QtCore import QObject, Signal
except Exception:  # pragma: no cover

    class QObject:  # type: ignore[no-redef]
        pass

    class Signal:  # type: ignore[no-redef]
        def __init__(self, *_: object, **__: object) -> None:
            pass

        def emit(self, *_: object, **__: object) -> None:
            return


from app.application.ports.integrations import (
    CometConfig,
    DVCConfig,
    IntegrationsPort,
    IntegrationsState,
    KFoldConfig,
    ModelExportConfig,
    ModelValidationConfig,
    SageMakerConfig,
    SahiConfig,
    SegIsolationConfig,
    TuningConfig,
)
from app.application.use_cases.export_model import DefaultModelExporter, ExportModelUseCase
from app.application.use_cases.integrations_config import (
    DefaultIntegrationsConfigRepository,
    ExportIntegrationsConfigRequest,
    ExportIntegrationsConfigUseCase,
    ImportIntegrationsConfigRequest,
    ImportIntegrationsConfigUseCase,
)
from app.application.use_cases.validate_model import DefaultModelValidator, ValidateModelUseCase

if TYPE_CHECKING:
    from app.ui.infrastructure.di import Container


class IntegrationsViewModel(QObject):
    """Application-facing API for the Integrations view."""

    state_changed = Signal(object)  # IntegrationsState

    def __init__(self, container: Container | None = None) -> None:
        super().__init__()
        self._container = container
        self._integrations: IntegrationsPort | None = None
        self._jobs: dict[str, JobHandle[Any] | ProcessJobHandle[Any]] = {}

    @property
    def integrations(self) -> IntegrationsPort:
        if self._integrations is None:
            if self._container is None:
                raise RuntimeError("Container is required for integrations operations")
            self._integrations = self._container.integrations
        return self._integrations

    def _policy_kwargs(
        self,
        *,
        min_timeout_sec: int = 0,
        min_retries: int = 0,
        min_backoff_sec: float = 0.0,
    ) -> dict[str, Any]:
        """Merge user-configured policy with per-action minimums."""
        p = self.integrations.load_jobs_policy()
        timeout = max(int(p.default_timeout_sec), int(min_timeout_sec))
        retries = max(int(p.retries), int(min_retries))
        backoff = max(float(p.retry_backoff_sec), float(min_backoff_sec))
        kwargs: dict[str, Any] = {
            "timeout_sec": timeout if timeout > 0 else None,
            "retries": retries,
            "retry_backoff_sec": backoff,
            "retry_jitter": float(p.retry_jitter),
            "retry_deadline_sec": int(p.retry_deadline_sec)
            if int(p.retry_deadline_sec) > 0
            else None,
        }
        return kwargs

    # ---- State ----
    def load_state(self) -> IntegrationsState:
        return self.integrations.load_state()

    def refresh_state(self) -> IntegrationsState:
        """Reload persisted configs and notify subscribers."""
        state = self.load_state()
        self.state_changed.emit(state)
        return state

    # ---- Import/Export full integrations config ----
    def export_integrations_config(self, path: Path) -> None:
        uc = (
            self._container.export_integrations_config_use_case
            if self._container
            else ExportIntegrationsConfigUseCase(DefaultIntegrationsConfigRepository())
        )
        uc.execute(ExportIntegrationsConfigRequest(path=path))

    def import_integrations_config(self, path: Path) -> None:
        uc = (
            self._container.import_integrations_config_use_case
            if self._container
            else ImportIntegrationsConfigUseCase(DefaultIntegrationsConfigRepository())
        )
        uc.execute(ImportIntegrationsConfigRequest(path=path))
        self.refresh_state()

    # ---- Save / reset sections ----
    def _update_state(self, **changes: Any) -> IntegrationsState:
        """Persist a single-section change via the IntegrationsPort."""
        state = self.load_state()
        new_state = replace(state, **changes)
        self.integrations.save_state(new_state)
        self.refresh_state()
        return new_state

    def save_comet(self, cfg: CometConfig) -> None:
        self._update_state(comet=cfg)

    def reset_comet(self) -> CometConfig:
        cfg = CometConfig(
            enabled=False,
            api_key="",
            project_name="yolo26-project",
            max_image_predictions=100,
            eval_batch_logging_interval=1,
            eval_log_confusion_matrix=True,
            mode="online",
        )
        self._update_state(comet=cfg)
        return cfg

    def save_dvc(self, cfg: DVCConfig) -> None:
        self._update_state(dvc=cfg)

    def reset_dvc(self) -> DVCConfig:
        cfg = DVCConfig(enabled=False)
        self._update_state(dvc=cfg)
        return cfg

    def save_sagemaker(self, cfg: SageMakerConfig) -> None:
        self._update_state(sagemaker=cfg)

    def reset_sagemaker(self) -> SageMakerConfig:
        cfg = SageMakerConfig(
            instance_type="ml.m5.4xlarge", endpoint_name="", model_path="", template_cloned_path=""
        )
        self._update_state(sagemaker=cfg)
        return cfg

    def save_kfold(self, cfg: KFoldConfig) -> None:
        self._update_state(kfold=cfg)

    def save_tuning(self, cfg: TuningConfig) -> None:
        self._update_state(tuning=cfg)

    def save_export(self, cfg: ModelExportConfig) -> None:
        self._update_state(model_export=cfg)

    def save_sahi(self, cfg: SahiConfig) -> None:
        self._update_state(sahi=cfg)

    def save_seg_isolation(self, cfg: SegIsolationConfig) -> None:
        self._update_state(seg_isolation=cfg)

    def save_validation(self, cfg: ModelValidationConfig) -> None:
        self._update_state(model_validation=cfg)

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

    def run_export(self, *, model_path: str, export_format: str, output_dir: str) -> str:
        cfg = ModelExportConfig(
            weights_path=model_path, format=export_format, output_dir=output_dir
        )
        return self.export_model_async(cfg)

    def run_validation(self, *, model_path: str, data_yaml: str) -> str:
        cfg = ModelValidationConfig(weights_path=model_path, data_yaml=data_yaml)
        return self.validate_model_async(cfg)

    # ---- Actions ----
    def export_model(self, cfg: ModelExportConfig) -> Path | None:
        uc = (
            self._container.export_model_use_case
            if self._container
            else ExportModelUseCase(DefaultModelExporter())
        )
        return uc.execute(cfg)

    def export_model_async(self, cfg: ModelExportConfig) -> str:
        if not self._container:
            # Fallback: run sync.
            self.export_model(cfg)
            return ""
        runner = self._container.job_runner

        def _fn(_cancel, progress) -> Path | None:
            progress(0.05, "exporting")
            out = self.export_model(cfg)
            progress(0.95, "finalizing")
            return out

        kwargs = self._policy_kwargs(min_timeout_sec=600)
        h = runner.submit("export_model", _fn, **kwargs)
        self._jobs[h.job_id] = h
        reg = self._container.job_registry
        reg.set_cancel(h.job_id, h.cancel)
        reg.set_rerun(
            h.job_id, lambda: self._container.job_runner.submit("export_model", _fn, **kwargs)
        )
        return h.job_id

    def validate_model(self, cfg: ModelValidationConfig) -> dict[str, Any]:
        uc = (
            self._container.validate_model_use_case
            if self._container
            else ValidateModelUseCase(DefaultModelValidator())
        )
        return uc.execute(cfg)

    def validate_model_async(self, cfg: ModelValidationConfig) -> str:
        if not self._container:
            self.validate_model(cfg)
            return ""
        runner = self._container.job_runner

        def _fn(_cancel, progress) -> dict[str, Any]:
            progress(0.05, "validating")
            res = self.validate_model(cfg)
            progress(0.95, "finalizing")
            return res

        kwargs = self._policy_kwargs(min_timeout_sec=900)
        h = runner.submit("validate_model", _fn, **kwargs)
        self._jobs[h.job_id] = h
        reg = self._container.job_registry
        reg.set_cancel(h.job_id, h.cancel)
        reg.set_rerun(
            h.job_id, lambda: self._container.job_runner.submit("validate_model", _fn, **kwargs)
        )
        return h.job_id

    def kfold_split(self, cfg: KFoldConfig) -> list[Path]:
        from app.features.kfold_integration.service import run_kfold_split

        return run_kfold_split(cfg)

    def kfold_split_async(self, cfg: KFoldConfig) -> str:
        if not self._container:
            self.kfold_split(cfg)
            return ""
        runner = self._container.job_runner

        def _fn(cancel, progress) -> list[Path]:
            progress(0.05, "splitting")
            if cancel.is_cancelled():
                raise CancelledError("cancelled")
            out = self.kfold_split(cfg)
            progress(0.95, "finalizing")
            return out

        h = runner.submit("kfold_split", _fn)
        self._jobs[h.job_id] = h
        reg = self._container.job_registry
        reg.set_cancel(h.job_id, h.cancel)
        reg.set_rerun(h.job_id, lambda: self._container.job_runner.submit("kfold_split", _fn))
        return h.job_id

    def kfold_train(self, cfg: KFoldConfig, yamls: list[Path]) -> list[Path]:
        from app.features.kfold_integration.service import run_kfold_train

        return run_kfold_train(cfg, yamls)

    def kfold_train_async(self, cfg: KFoldConfig, yamls: list[Path]) -> str:
        if not self._container:
            self.kfold_train(cfg, yamls)
            return ""
        runner = self._container.job_runner

        def _fn(cancel, progress) -> list[Path]:
            progress(0.05, "training")
            if cancel.is_cancelled():
                raise CancelledError("cancelled")
            out = self.kfold_train(cfg, yamls)
            progress(0.95, "finalizing")
            return out

        h = runner.submit("kfold_train", _fn)
        self._jobs[h.job_id] = h
        reg = self._container.job_registry
        reg.set_cancel(h.job_id, h.cancel)
        reg.set_rerun(h.job_id, lambda: self._container.job_runner.submit("kfold_train", _fn))
        return h.job_id

    def tune(self, cfg: TuningConfig) -> Path:
        from app.features.hyperparameter_tuning.service import run_tune

        return run_tune(cfg)

    def tune_async(self, cfg: TuningConfig) -> str:
        if not self._container:
            self.tune(cfg)
            return ""
        # Tuning can be heavy; run in a separate process for hard timeout/cancel.
        runner = self._container.process_job_runner
        fn = partial(tune_job, cfg=cfg)
        kwargs = self._policy_kwargs(min_timeout_sec=1200)
        h = runner.submit("tune", fn, **kwargs)
        self._jobs[h.job_id] = h
        reg = self._container.job_registry
        reg.set_cancel(h.job_id, h.cancel)
        reg.set_rerun(
            h.job_id, lambda: self._container.process_job_runner.submit("tune", fn, **kwargs)
        )
        return h.job_id

    def sahi_predict(self, cfg: SahiConfig) -> None:
        from app.features.sahi_integration.service import run_sahi_predict

        run_sahi_predict(cfg)

    def sahi_predict_async(self, cfg: SahiConfig) -> str:
        if not self._container:
            self.sahi_predict(cfg)
            return ""
        # SAHI runs third-party code and may hang; run in a separate process.
        runner = self._container.process_job_runner
        fn = partial(sahi_predict_job, cfg=cfg)
        kwargs = self._policy_kwargs(min_timeout_sec=900)
        h = runner.submit("sahi_predict", fn, **kwargs)
        self._jobs[h.job_id] = h
        reg = self._container.job_registry
        reg.set_cancel(h.job_id, h.cancel)
        reg.set_rerun(
            h.job_id,
            lambda: self._container.process_job_runner.submit("sahi_predict", fn, **kwargs),
        )
        return h.job_id

    def seg_isolate(self, cfg: SegIsolationConfig) -> int:
        from app.features.segmentation_isolation.service import run_seg_isolation

        return run_seg_isolation(cfg)

    def seg_isolate_async(self, cfg: SegIsolationConfig) -> str:
        if not self._container:
            self.seg_isolate(cfg)
            return ""
        runner = self._container.job_runner

        def _fn(cancel, progress) -> int:
            progress(0.05, "running")
            # run_seg_isolation doesn't support cancellation; check token early.
            if cancel.is_cancelled():
                raise CancelledError("cancelled")
            res = self.seg_isolate(cfg)
            progress(0.95, "finalizing")
            return res

        h = runner.submit("seg_isolate", _fn)
        self._jobs[h.job_id] = h
        reg = self._container.job_registry
        reg.set_cancel(h.job_id, h.cancel)
        reg.set_rerun(h.job_id, lambda: self._container.job_runner.submit("seg_isolate", _fn))
        return h.job_id

    def cancel_job(self, job_id: str) -> bool:
        h = self._jobs.get(job_id)
        if not h:
            return False
        h.cancel()
        return True

    def sagemaker_clone_template(self, base_dir: Path | None) -> tuple[bool, str]:
        from app.features.sagemaker_integration.service import clone_sagemaker_template

        return clone_sagemaker_template(base_dir)

    def sagemaker_clone_template_async(self, base_dir: Path | None) -> str:
        if not self._container:
            self.sagemaker_clone_template(base_dir)
            return ""
        # External tooling / git operations: run in a process for hard timeout.
        runner = self._container.process_job_runner
        fn = partial(sagemaker_clone_template_job, base_dir=base_dir)
        kwargs = self._policy_kwargs(min_timeout_sec=600, min_retries=1, min_backoff_sec=2.0)
        h = runner.submit("sagemaker_clone_template", fn, **kwargs)
        self._jobs[h.job_id] = h
        reg = self._container.job_registry
        reg.set_cancel(h.job_id, h.cancel)
        reg.set_rerun(
            h.job_id,
            lambda: self._container.process_job_runner.submit(
                "sagemaker_clone_template", fn, **kwargs
            ),
        )
        return h.job_id

    def sagemaker_cdk_deploy(self, template_dir: Path) -> tuple[bool, str]:
        from app.features.sagemaker_integration.service import run_cdk_deploy

        return run_cdk_deploy(template_dir)

    def sagemaker_cdk_deploy_async(self, template_dir: Path) -> str:
        if not self._container:
            self.sagemaker_cdk_deploy(template_dir)
            return ""
        runner = self._container.process_job_runner
        fn = partial(sagemaker_cdk_deploy_job, template_dir=template_dir)
        kwargs = self._policy_kwargs(min_timeout_sec=1800, min_retries=2, min_backoff_sec=3.0)
        h = runner.submit("sagemaker_cdk_deploy", fn, **kwargs)
        self._jobs[h.job_id] = h
        reg = self._container.job_registry
        reg.set_cancel(h.job_id, h.cancel)
        reg.set_rerun(
            h.job_id,
            lambda: self._container.process_job_runner.submit("sagemaker_cdk_deploy", fn, **kwargs),
        )
        return h.job_id
