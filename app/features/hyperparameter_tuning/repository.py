"""Load/save tuning config from integrations config."""

from __future__ import annotations

from app.features.integrations_config import load_config, save_config
from app.features.hyperparameter_tuning.domain import TuningConfig


def load_tuning_config() -> TuningConfig:
    config = load_config()
    return TuningConfig.from_dict(config.get("tuning"))


def save_tuning_config(cfg: TuningConfig) -> None:
    config = load_config()
    config["tuning"] = cfg.to_dict()
    save_config(config)
