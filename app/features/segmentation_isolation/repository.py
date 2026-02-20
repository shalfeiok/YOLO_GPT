"""Load/save seg isolation config from integrations config."""

from __future__ import annotations

from app.features.integrations_config import load_config, save_config
from app.features.segmentation_isolation.domain import SegIsolationConfig


def load_seg_isolation_config() -> SegIsolationConfig:
    config = load_config()
    return SegIsolationConfig.from_dict(config.get("seg_isolation"))


def save_seg_isolation_config(cfg: SegIsolationConfig) -> None:
    config = load_config()
    config["seg_isolation"] = cfg.to_dict()
    save_config(config)
