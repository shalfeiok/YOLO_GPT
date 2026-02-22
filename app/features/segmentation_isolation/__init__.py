"""Isolating segmentation objects.

NOTE: UI is not imported at package import-time (headless-safe).
Ref: https://docs.ultralytics.com/ru/guides/isolating-segmentation-objects/
"""

from app.features.segmentation_isolation.domain import SegIsolationConfig
from app.features.segmentation_isolation.repository import (
    load_seg_isolation_config,
    save_seg_isolation_config,
)
from app.features.segmentation_isolation.service import run_seg_isolation

__all__ = [
    "SegIsolationConfig",
    "load_seg_isolation_config",
    "save_seg_isolation_config",
    "run_seg_isolation",
]
