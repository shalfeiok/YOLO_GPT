from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.training_config import TrainingConfig


@dataclass(frozen=True, slots=True)
class RecommendationItem:
    param: str
    current: Any
    recommended: Any
    reason: str
    confidence: float


@dataclass(frozen=True, slots=True)
class AdvisorReport:
    dataset_health: dict[str, Any]
    run_summary: dict[str, Any]
    model_eval: dict[str, Any]
    recommendations: list[RecommendationItem]
    recommended_training_config: TrainingConfig
    diff: list[dict[str, Any]]
    warnings: list[str]
    errors: list[str]
