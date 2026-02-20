"""Load/save K-Fold config from integrations config."""

from __future__ import annotations

from app.features.integrations_config import load_config, save_config
from app.features.kfold_integration.domain import KFoldConfig


def load_kfold_config() -> KFoldConfig:
    config = load_config()
    return KFoldConfig.from_dict(config.get("kfold"))


def save_kfold_config(cfg: KFoldConfig) -> None:
    config = load_config()
    config["kfold"] = cfg.to_dict()
    save_config(config)
