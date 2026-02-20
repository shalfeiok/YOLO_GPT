"""
Run model.val(data=...) and return metrics (mAP50, mAP50-95, precision, recall, etc.).

Ref: https://docs.ultralytics.com/ru/guides/model-evaluation-insights/
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.features.model_validation.domain import ModelValidationConfig


def run_validation(
    cfg: ModelValidationConfig,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, float]:
    """Run model.val(), return dict of key metrics."""
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError("Ultralytics required: pip install ultralytics")

    if not cfg.data_yaml or not Path(cfg.data_yaml).exists():
        raise FileNotFoundError(f"Data YAML not found: {cfg.data_yaml}")
    weights = cfg.weights_path.strip() or "yolo11n.pt"
    if weights and not weights.startswith("yolo") and not Path(weights).exists():
        raise FileNotFoundError(f"Weights not found: {weights}")

    if on_progress:
        on_progress("Запуск валидации…")
    model = YOLO(weights, task="detect")
    results = model.val(data=cfg.data_yaml, verbose=True)
    out = {}
    if hasattr(results, "box"):
        b = results.box
        for key in ("map50", "map", "mp", "mr", "fitness"):
            if hasattr(b, key):
                val = getattr(b, key)
                if hasattr(val, "item"):
                    out[key] = float(val.item())
                else:
                    out[key] = float(val)
    if on_progress:
        on_progress("Готово.")
    return out
