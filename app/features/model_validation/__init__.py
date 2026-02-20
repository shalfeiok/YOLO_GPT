"""Model validation (model.val) and metrics.

NOTE: UI is not imported at package import-time (headless-safe).
Ref: https://docs.ultralytics.com/ru/guides/model-evaluation-insights/
"""

from app.features.model_validation.domain import ModelValidationConfig
from app.features.model_validation.repository import load_validation_config, save_validation_config
from app.features.model_validation.service import run_validation

__all__ = [
    "ModelValidationConfig",
    "load_validation_config",
    "save_validation_config",
    "run_validation",
]
