"""Read/write Albumentations section from integrations config (delegates to integrations_config)."""

from app.features.albumentations_integration.domain import AlbumentationsConfig
from app.features.integrations_config import load_config, save_config


def load_albumentations_config() -> AlbumentationsConfig:
    """Load Albumentations config from global integrations JSON."""
    data = load_config()
    return AlbumentationsConfig.from_dict(data.get("albumentations", {}))


def save_albumentations_config(cfg: AlbumentationsConfig) -> None:
    """Save Albumentations config into global integrations JSON."""
    data = load_config()
    data["albumentations"] = cfg.to_dict()
    save_config(data)
