"""
Run YOLO hyperparameter tuning (model.tune) in a thread.

Ref: https://docs.ultralytics.com/ru/guides/hyperparameter-tuning/
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.features.hyperparameter_tuning.domain import TuningConfig


def run_tune(
    cfg: TuningConfig,
    on_progress: Callable[[str], None] | None = None,
) -> Path | None:
    """
    Run model.tune(data=..., epochs=..., iterations=...).
    Returns path to tune results dir (runs/detect/tune) or None on error.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError("Ultralytics required: pip install ultralytics")

    if not cfg.data_yaml or not Path(cfg.data_yaml).exists():
        raise FileNotFoundError(f"Data YAML not found: {cfg.data_yaml}")

    model_path = cfg.model_path.strip() or "yolo11n.pt"
    if model_path and not model_path.endswith(".pt") and Path(model_path).exists():
        pass  # path to .pt file
    elif model_path and not model_path.startswith("yolo"):
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model weights not found: {model_path}")

    if on_progress:
        on_progress("Запуск настройки гиперпараметров…")

    model = YOLO(model_path, task="detect")
    result = model.tune(
        data=cfg.data_yaml,
        epochs=cfg.epochs,
        iterations=cfg.iterations,
        project=cfg.project,
        name=cfg.name,
        plots=False,
        save=False,
        val=False,
    )

    if on_progress:
        on_progress("Настройка завершена.")

    # result is a list of Results; best dir is typically project/name
    out = Path(cfg.project) / cfg.name
    return out if out.exists() else None
