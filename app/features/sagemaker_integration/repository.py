"""Read/write SageMaker section from integrations config."""

from app.features.integrations_config import load_config, save_config
from app.features.sagemaker_integration.domain import SageMakerConfig


def load_sagemaker_config() -> SageMakerConfig:
    data = load_config()
    return SageMakerConfig.from_dict(data.get("sagemaker", {}))


def save_sagemaker_config(cfg: SageMakerConfig) -> None:
    data = load_config()
    data["sagemaker"] = cfg.to_dict()
    save_config(data)
