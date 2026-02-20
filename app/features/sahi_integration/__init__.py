"""SAHI tiled inference.

NOTE: UI is not imported at package import-time (headless-safe).
Ref: https://docs.ultralytics.com/ru/guides/sahi-tiled-inference/
"""

from app.features.sahi_integration.domain import SahiConfig
from app.features.sahi_integration.repository import load_sahi_config, save_sahi_config
from app.features.sahi_integration.service import run_sahi_predict

__all__ = [
    "SahiConfig",
    "load_sahi_config",
    "save_sahi_config",
    "run_sahi_predict",
]
