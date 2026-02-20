"""
Run SAHI tiled inference (sliced prediction) on a directory.

Ref: https://docs.ultralytics.com/ru/guides/sahi-tiled-inference/
Requires: pip install sahi
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.features.sahi_integration.domain import SahiConfig


def run_sahi_predict(
    cfg: SahiConfig,
    on_progress: Callable[[str], None] | None = None,
) -> Path | None:
    """
    Run SAHI predict() on source dir with slice params.
    Returns path to output dir or None. Requires sahi package.
    """
    try:
        from sahi.predict import predict
    except ImportError:
        raise ImportError("SAHI required: pip install sahi")

    if not cfg.model_path:
        raise ValueError("Укажите путь к модели (.pt)")
    if not cfg.source_dir or not Path(cfg.source_dir).exists():
        raise FileNotFoundError(f"Папка с изображениями не найдена: {cfg.source_dir}")

    if on_progress:
        on_progress("Запуск SAHI tiled inference…")

    predict(
        model_type="ultralytics",
        model_path=cfg.model_path,
        model_device="cpu",
        model_confidence_threshold=cfg.confidence_threshold,
        source=cfg.source_dir,
        slice_height=cfg.slice_height,
        slice_width=cfg.slice_width,
        overlap_height_ratio=cfg.overlap_height_ratio,
        overlap_width_ratio=cfg.overlap_width_ratio,
    )

    if on_progress:
        on_progress("Готово.")
    return Path(cfg.source_dir)
