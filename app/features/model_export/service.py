"""
Export YOLO model to ONNX, OpenVINO, TensorFlow, etc.

Ref: https://docs.ultralytics.com/ru/guides/model-deployment-options/#tf-graphdef
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.features.model_export.domain import EXPORT_FORMATS, ModelExportConfig


def run_export(
    cfg: ModelExportConfig,
    on_progress: Callable[[str], None] | None = None,
) -> Path | None:
    """
    Run model.export(format=...). Returns path to exported file/dir or None.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError("Ultralytics required: pip install ultralytics")

    if not cfg.weights_path:
        raise ValueError("Укажите путь к весам (.pt)")
    fmt = (cfg.format or "onnx").strip().lower()
    if fmt not in EXPORT_FORMATS:
        fmt = "onnx"

    if on_progress:
        on_progress(f"Экспорт в {fmt}…")

    model = YOLO(cfg.weights_path)
    result = model.export(
        format=fmt,
        imgsz=640,
    )
    # result is path to exported file
    out = Path(result) if result else None
    if on_progress and out:
        on_progress(f"Готово: {out}")
    return out
