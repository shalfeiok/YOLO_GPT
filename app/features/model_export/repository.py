"""Load/save model export config from integrations config."""

from __future__ import annotations

from app.features.integrations_config import load_config, save_config
from app.features.model_export.domain import ModelExportConfig


def load_export_config() -> ModelExportConfig:
    config = load_config()
    return ModelExportConfig.from_dict(config.get("model_export"))


def save_export_config(cfg: ModelExportConfig) -> None:
    config = load_config()
    config["model_export"] = cfg.to_dict()
    save_config(config)
