"""Load/save SAHI config from integrations config."""

from __future__ import annotations

from app.features.integrations_config import load_config, save_config
from app.features.sahi_integration.domain import SahiConfig


def load_sahi_config() -> SahiConfig:
    config = load_config()
    return SahiConfig.from_dict(config.get("sahi"))


def save_sahi_config(cfg: SahiConfig) -> None:
    config = load_config()
    config["sahi"] = cfg.to_dict()
    save_config(config)
