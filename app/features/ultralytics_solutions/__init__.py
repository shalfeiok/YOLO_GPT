"""Ultralytics Solutions: Distance, Heatmap, ObjectCounter, RegionCounter, SpeedEstimator, TrackZone.

NOTE: UI is not imported at package import-time (headless-safe).
"""

from app.features.ultralytics_solutions.domain import SOLUTION_TYPES, SolutionsConfig
from app.features.ultralytics_solutions.repository import load_solutions_config, save_solutions_config
from app.features.ultralytics_solutions.service import run_solution

__all__ = [
    "SOLUTION_TYPES",
    "SolutionsConfig",
    "load_solutions_config",
    "save_solutions_config",
    "run_solution",
]
