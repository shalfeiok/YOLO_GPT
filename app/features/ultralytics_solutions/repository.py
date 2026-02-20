"""Load/save solutions config from integrations config."""

from __future__ import annotations

from app.features.integrations_config import load_config, save_config
from app.features.ultralytics_solutions.domain import SolutionsConfig


def load_solutions_config() -> SolutionsConfig:
    config = load_config()
    return SolutionsConfig.from_dict(config.get("ultralytics_solutions"))


def save_solutions_config(cfg: SolutionsConfig) -> None:
    config = load_config()
    config["ultralytics_solutions"] = cfg.to_dict()
    save_config(config)
