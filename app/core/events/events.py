from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TrainingStarted:
    model_name: str
    epochs: int
    project: Path


@dataclass(frozen=True, slots=True)
class TrainingProgress:
    fraction: float
    message: str


@dataclass(frozen=True, slots=True)
class TrainingFinished:
    best_weights_path: Path | None


@dataclass(frozen=True, slots=True)
class TrainingCancelled:
    message: str = "Training cancelled"


@dataclass(frozen=True, slots=True)
class TrainingFailed:
    error: Exception
