"""Load/save validation config from integrations config."""

from __future__ import annotations

from app.features.integrations_config import load_config, save_config
from app.features.model_validation.domain import ModelValidationConfig


def load_validation_config() -> ModelValidationConfig:
    config = load_config()
    return ModelValidationConfig.from_dict(config.get("model_validation"))


def save_validation_config(cfg: ModelValidationConfig) -> None:
    config = load_config()
    config["model_validation"] = cfg.to_dict()
    save_config(config)
