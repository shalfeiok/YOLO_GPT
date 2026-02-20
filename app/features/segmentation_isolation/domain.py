"""
Domain for isolating segmentation objects (mask → crop, black or transparent bg).

Ref: https://docs.ultralytics.com/ru/guides/isolating-segmentation-objects/
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SegIsolationConfig:
    model_path: str = ""
    source_path: str = ""  # image or dir
    output_dir: str = ""
    background: str = "black"  # "black" | "transparent"
    crop: bool = True  # crop to bbox else full image

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_path": self.model_path,
            "source_path": self.source_path,
            "output_dir": self.output_dir,
            "background": self.background,
            "crop": self.crop,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> SegIsolationConfig:
        if not d:
            return cls()
        return cls(
            model_path=str(d.get("model_path", "")),
            source_path=str(d.get("source_path", "")),
            output_dir=str(d.get("output_dir", "")),
            background=str(d.get("background", "black")),
            crop=bool(d.get("crop", True)),
        )
