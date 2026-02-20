"""
Domain models for Albumentations integration.

Ref: https://docs.ultralytics.com/ru/integrations/albumentations/
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class AlbumentationsConfig:
    """Config for Albumentations during training."""

    enabled: bool
    use_standard: bool
    custom_transforms: list[dict[str, Any]]  # list of {name, p, ...params}
    transform_p: float

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AlbumentationsConfig":
        return cls(
            enabled=bool(d.get("enabled", False)),
            use_standard=bool(d.get("use_standard", True)),
            custom_transforms=list(d.get("custom_transforms", [])),
            transform_p=float(d.get("transform_p", 0.5)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "use_standard": self.use_standard,
            "custom_transforms": self.custom_transforms,
            "transform_p": self.transform_p,
        }


# Built-in transform names supported in UI (match Albumentations API)
STANDARD_TRANSFORM_NAMES = [
    "Blur",
    "MedianBlur",
    "ToGray",
    "CLAHE",
    "GaussNoise",
    "RandomBrightnessContrast",
    "HueSaturationValue",
]
