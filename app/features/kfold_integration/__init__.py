"""K-Fold Cross Validation integration.

NOTE: UI is not imported at package import-time (headless-safe).
Ref: https://docs.ultralytics.com/ru/guides/kfold-cross-validation/
"""

from app.features.kfold_integration.domain import KFoldConfig
from app.features.kfold_integration.repository import load_kfold_config, save_kfold_config
from app.features.kfold_integration.service import run_kfold_split, run_kfold_train

__all__ = [
    "KFoldConfig",
    "load_kfold_config",
    "save_kfold_config",
    "run_kfold_split",
    "run_kfold_train",
]
