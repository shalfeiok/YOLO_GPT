from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

from app.application.jobs.risky_job_fns import (
    sagemaker_cdk_deploy_job,
    sagemaker_clone_template_job,
    sahi_predict_job,
    tune_job,
)
from app.application.ports.integrations import KFoldConfig, ModelExportConfig, ModelValidationConfig, SahiConfig, SegIsolationConfig, TuningConfig
from app.application.use_cases.export_model import DefaultModelExporter, ExportModelUseCase
from app.application.use_cases.validate_model import DefaultModelValidator, ValidateModelUseCase
from app.core.errors import CancelledError


class IntegrationsActionsMixin:
    def run_export(self, *, model_path: str, export_format: str, output_dir: str) -> str:
        return self.export_model_async(ModelExportConfig(weights_path=model_path, format=export_format, output_dir=output_dir))

    def run_validation(self, *, model_path: str, data_yaml: str) -> str:
        return self.validate_model_async(ModelValidationConfig(weights_path=model_path, data_yaml=data_yaml))

    def export_model(self, cfg: ModelExportConfig) -> Path | None:
        uc = self._container.export_model_use_case if self._container else ExportModelUseCase(DefaultModelExporter())
        return uc.execute(cfg)

    def validate_model(self, cfg: ModelValidationConfig) -> dict[str, Any]:
        uc = self._container.validate_model_use_case if self._container else ValidateModelUseCase(DefaultModelValidator())
        return uc.execute(cfg)

    def kfold_split(self, cfg: KFoldConfig) -> list[Path]:
        from app.features.kfold_integration.service import run_kfold_split

        return run_kfold_split(cfg)

    def kfold_train(self, cfg: KFoldConfig, yamls: list[Path]) -> list[Path]:
        from app.features.kfold_integration.service import run_kfold_train

        return run_kfold_train(cfg, yamls)

    def tune(self, cfg: TuningConfig) -> Path:
        from app.features.hyperparameter_tuning.service import run_tune

        return run_tune(cfg)

    def sahi_predict(self, cfg: SahiConfig) -> None:
        from app.features.sahi_integration.service import run_sahi_predict

        run_sahi_predict(cfg)

    def seg_isolate(self, cfg: SegIsolationConfig) -> int:
        from app.features.segmentation_isolation.service import run_seg_isolation

        return run_seg_isolation(cfg)

    def sagemaker_clone_template(self, base_dir: Path | None) -> tuple[bool, str]:
        from app.features.sagemaker_integration.service import clone_sagemaker_template

        return clone_sagemaker_template(base_dir)

    def sagemaker_cdk_deploy(self, template_dir: Path) -> tuple[bool, str]:
        from app.features.sagemaker_integration.service import run_cdk_deploy

        return run_cdk_deploy(template_dir)

    def _submit_thread_job(self, name: str, fn, **kwargs: Any) -> str:
        h = self._container.job_runner.submit(name, fn, **kwargs)
        self._jobs[h.job_id] = h
        reg = self._container.job_registry
        reg.set_cancel(h.job_id, h.cancel)
        reg.set_rerun(h.job_id, lambda: self._container.job_runner.submit(name, fn, **kwargs))
        return h.job_id

    def _submit_process_job(self, name: str, fn, **kwargs: Any) -> str:
        h = self._container.process_job_runner.submit(name, fn, **kwargs)
        self._jobs[h.job_id] = h
        reg = self._container.job_registry
        reg.set_cancel(h.job_id, h.cancel)
        reg.set_rerun(h.job_id, lambda: self._container.process_job_runner.submit(name, fn, **kwargs))
        return h.job_id

    def export_model_async(self, cfg: ModelExportConfig) -> str:
        if not self._container:
            self.export_model(cfg)
            return ""

        def _fn(_cancel, progress) -> Path | None:
            progress(0.05, "exporting")
            out = self.export_model(cfg)
            progress(0.95, "finalizing")
            return out

        return self._submit_thread_job("export_model", _fn, **self._policy_kwargs(min_timeout_sec=600))

    def validate_model_async(self, cfg: ModelValidationConfig) -> str:
        if not self._container:
            self.validate_model(cfg)
            return ""

        def _fn(_cancel, progress) -> dict[str, Any]:
            progress(0.05, "validating")
            res = self.validate_model(cfg)
            progress(0.95, "finalizing")
            return res

        return self._submit_thread_job("validate_model", _fn, **self._policy_kwargs(min_timeout_sec=900))

    def kfold_split_async(self, cfg: KFoldConfig) -> str:
        if not self._container:
            self.kfold_split(cfg)
            return ""

        def _fn(cancel, progress) -> list[Path]:
            progress(0.05, "splitting")
            if cancel.is_cancelled():
                raise CancelledError("cancelled")
            out = self.kfold_split(cfg)
            progress(0.95, "finalizing")
            return out

        return self._submit_thread_job("kfold_split", _fn)

    def kfold_train_async(self, cfg: KFoldConfig, yamls: list[Path]) -> str:
        if not self._container:
            self.kfold_train(cfg, yamls)
            return ""

        def _fn(cancel, progress) -> list[Path]:
            progress(0.05, "training")
            if cancel.is_cancelled():
                raise CancelledError("cancelled")
            out = self.kfold_train(cfg, yamls)
            progress(0.95, "finalizing")
            return out

        return self._submit_thread_job("kfold_train", _fn)

    def tune_async(self, cfg: TuningConfig) -> str:
        if not self._container:
            self.tune(cfg)
            return ""
        return self._submit_process_job("tune", partial(tune_job, cfg=cfg), **self._policy_kwargs(min_timeout_sec=1200))

    def sahi_predict_async(self, cfg: SahiConfig) -> str:
        if not self._container:
            self.sahi_predict(cfg)
            return ""
        return self._submit_process_job("sahi_predict", partial(sahi_predict_job, cfg=cfg), **self._policy_kwargs(min_timeout_sec=900))

    def seg_isolate_async(self, cfg: SegIsolationConfig) -> str:
        if not self._container:
            self.seg_isolate(cfg)
            return ""

        def _fn(cancel, progress) -> int:
            progress(0.05, "running")
            if cancel.is_cancelled():
                raise CancelledError("cancelled")
            res = self.seg_isolate(cfg)
            progress(0.95, "finalizing")
            return res

        return self._submit_thread_job("seg_isolate", _fn)

    def sagemaker_clone_template_async(self, base_dir: Path | None) -> str:
        if not self._container:
            self.sagemaker_clone_template(base_dir)
            return ""
        return self._submit_process_job("sagemaker_clone_template", partial(sagemaker_clone_template_job, base_dir=base_dir), **self._policy_kwargs(min_timeout_sec=600, min_retries=1, min_backoff_sec=2.0))

    def sagemaker_cdk_deploy_async(self, template_dir: Path) -> str:
        if not self._container:
            self.sagemaker_cdk_deploy(template_dir)
            return ""
        return self._submit_process_job("sagemaker_cdk_deploy", partial(sagemaker_cdk_deploy_job, template_dir=template_dir), **self._policy_kwargs(min_timeout_sec=1800, min_retries=2, min_backoff_sec=3.0))

    def cancel_job(self, job_id: str) -> bool:
        h = self._jobs.get(job_id)
        if not h:
            return False
        h.cancel()
        return True
