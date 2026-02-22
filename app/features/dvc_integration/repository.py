"""Read/write DVC section from integrations config."""

from app.features.dvc_integration.domain import DVCConfig
from app.features.integrations_config import load_config, save_config


def load_dvc_config() -> DVCConfig:
    data = load_config()
    return DVCConfig.from_dict(data.get("dvc", {}))


def save_dvc_config(cfg: DVCConfig) -> None:
    data = load_config()
    data["dvc"] = cfg.to_dict()
    save_config(data)
