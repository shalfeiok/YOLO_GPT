"""
Domain for SAHI tiled inference (sliced inference for large images).

Ref: https://docs.ultralytics.com/ru/guides/sahi-tiled-inference/
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SahiConfig:
    model_path: str = ""
    source_dir: str = ""
    slice_height: int = 256
    slice_width: int = 256
    overlap_height_ratio: float = 0.2
    overlap_width_ratio: float = 0.2
    confidence_threshold: float = 0.4

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_path": self.model_path,
            "source_dir": self.source_dir,
            "slice_height": self.slice_height,
            "slice_width": self.slice_width,
            "overlap_height_ratio": self.overlap_height_ratio,
            "overlap_width_ratio": self.overlap_width_ratio,
            "confidence_threshold": self.confidence_threshold,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> SahiConfig:
        if not d:
            return cls()
        return cls(
            model_path=str(d.get("model_path", "")),
            source_dir=str(d.get("source_dir", "")),
            slice_height=int(d.get("slice_height", 256)),
            slice_width=int(d.get("slice_width", 256)),
            overlap_height_ratio=float(d.get("overlap_height_ratio", 0.2)),
            overlap_width_ratio=float(d.get("overlap_width_ratio", 0.2)),
            confidence_threshold=float(d.get("confidence_threshold", 0.4)),
        )
