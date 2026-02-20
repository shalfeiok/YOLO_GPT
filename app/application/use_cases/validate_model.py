"""Model validation use case (application layer)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from app.features.model_validation.domain import ModelValidationConfig
from app.features.model_validation.service import run_validation


class ModelValidatorPort(Protocol):
    """Port the application layer needs for model validation."""

    def validate(
        self, config: ModelValidationConfig, *, on_progress: Callable[[float, str], None] | None = None
    ) -> dict[str, Any]:
        ...


class DefaultModelValidator:
    """Adapter over the feature-level validation service."""

    def validate(
        self, config: ModelValidationConfig, *, on_progress: Callable[[float, str], None] | None = None
    ) -> dict[str, Any]:
        return run_validation(config, on_progress=on_progress)


class ValidateModelUseCase:
    """Validate a model and return metrics."""

    def __init__(self, validator: ModelValidatorPort) -> None:
        self._validator = validator

    def execute(
        self, config: ModelValidationConfig, *, on_progress: Callable[[float, str], None] | None = None
    ) -> dict[str, Any]:
        return self._validator.validate(config, on_progress=on_progress)
