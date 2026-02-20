"""Picklable job functions for ProcessJobRunner.

These must be top-level callables so they can be pickled and executed in a
separate process (spawn start method).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from app.core.errors import CancelledError


def _progress(progress: Callable[[float, str | None], None], p: float, msg: str | None) -> None:
    pp = 0.0 if p < 0 else 1.0 if p > 1 else p
    progress(pp, msg)


def sahi_predict_job(cancel_evt: Any, progress: Callable[[float, str | None], None], cfg: Any) -> None:
    if cancel_evt.is_set():
        raise CancelledError("cancelled")
    _progress(progress, 0.05, "running")
    from app.features.sahi_integration.service import run_sahi_predict

    run_sahi_predict(cfg)
    _progress(progress, 0.95, "finalizing")
    return None


def sagemaker_clone_template_job(
    cancel_evt: Any,
    progress: Callable[[float, str | None], None],
    base_dir: Path | None,
) -> tuple[bool, str]:
    if cancel_evt.is_set():
        raise CancelledError("cancelled")
    _progress(progress, 0.05, "cloning")
    from app.features.sagemaker_integration.service import clone_sagemaker_template

    out = clone_sagemaker_template(base_dir)
    _progress(progress, 0.95, "finalizing")
    return out


def sagemaker_cdk_deploy_job(
    cancel_evt: Any,
    progress: Callable[[float, str | None], None],
    template_dir: Path,
) -> tuple[bool, str]:
    if cancel_evt.is_set():
        raise CancelledError("cancelled")
    _progress(progress, 0.05, "deploying")
    from app.features.sagemaker_integration.service import run_cdk_deploy

    out = run_cdk_deploy(template_dir)
    _progress(progress, 0.95, "finalizing")
    return out


def tune_job(cancel_evt: Any, progress: Callable[[float, str | None], None], cfg: Any) -> Path:
    if cancel_evt.is_set():
        raise CancelledError("cancelled")
    _progress(progress, 0.05, "tuning")
    from app.features.hyperparameter_tuning.service import run_tune

    out = run_tune(cfg)
    _progress(progress, 0.95, "finalizing")
    return out
