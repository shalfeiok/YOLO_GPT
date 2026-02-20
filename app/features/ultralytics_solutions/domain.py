"""
Domain for Ultralytics Solutions: Distance, Heatmap, ObjectCounter, RegionCounter, SpeedEstimator, TrackZone.

Refs: docs.ultralytics.com/ru/guides/distance-calculation/, heatmaps/, object-counting/, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SOLUTION_TYPES = [
    "DistanceCalculation",
    "Heatmap",
    "ObjectCounter",
    "RegionCounter",
    "SpeedEstimator",
    "TrackZone",
]


@dataclass
class SolutionsConfig:
    solution_type: str = "ObjectCounter"
    model_path: str = ""
    source: str = ""  # video path or 0 for webcam
    output_path: str = ""
    region_points: str = "[(20, 400), (1260, 400)]"  # for Counter/Region/TrackZone
    fps: float = 30.0  # for SpeedEstimator
    colormap: str = "COLORMAP_JET"  # for Heatmap

    def to_dict(self) -> dict[str, Any]:
        return {
            "solution_type": self.solution_type,
            "model_path": self.model_path,
            "source": self.source,
            "output_path": self.output_path,
            "region_points": self.region_points,
            "fps": self.fps,
            "colormap": self.colormap,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> SolutionsConfig:
        if not d:
            return cls()
        return cls(
            solution_type=str(d.get("solution_type", "ObjectCounter")),
            model_path=str(d.get("model_path", "")),
            source=str(d.get("source", "")),
            output_path=str(d.get("output_path", "")),
            region_points=str(d.get("region_points", "[(20, 400), (1260, 400)]")),
            fps=float(d.get("fps", 30.0)),
            colormap=str(d.get("colormap", "COLORMAP_JET")),
        )
