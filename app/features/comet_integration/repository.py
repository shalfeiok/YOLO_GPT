"""Read/write Comet section from integrations config."""

from app.features.comet_integration.domain import CometConfig
from app.features.integrations_config import load_config, save_config


def load_comet_config() -> CometConfig:
    data = load_config()
    return CometConfig.from_dict(data.get("comet", {}))


def save_comet_config(cfg: CometConfig) -> None:
    data = load_config()
    data["comet"] = cfg.to_dict()
    save_config(data)
