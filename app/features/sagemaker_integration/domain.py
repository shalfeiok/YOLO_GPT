"""
Domain for Amazon SageMaker deployment.

Ref: https://docs.ultralytics.com/ru/integrations/amazon-sagemaker/
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class SageMakerConfig:
    instance_type: str
    endpoint_name: str
    model_path: str
    template_cloned_path: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SageMakerConfig":
        return cls(
            instance_type=str(d.get("instance_type", "ml.m5.4xlarge")),
            endpoint_name=str(d.get("endpoint_name", "")),
            model_path=str(d.get("model_path", "")),
            template_cloned_path=str(d.get("template_cloned_path", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_type": self.instance_type,
            "endpoint_name": self.endpoint_name,
            "model_path": self.model_path,
            "template_cloned_path": self.template_cloned_path,
        }
