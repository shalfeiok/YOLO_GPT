"""Shared error types.

The goal is to make errors explicit and easy to handle at the UI boundary.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(eq=False)
class AppError(Exception):
    """Base error for application-level failures."""

    message: str
    cause: Exception | None = None

    def __str__(self) -> str:  # pragma: no cover
        if self.cause is None:
            return self.message
        return f"{self.message} (cause: {self.cause})"


class DomainError(AppError):
    """Domain rule violation."""


class ValidationError(AppError):
    """Invalid user input or configuration."""


class IntegrationError(AppError):
    """External integration failed."""


class InfrastructureError(AppError):
    """IO/OS/driver/FS failures."""


class CancelledError(AppError):
    """User-initiated cancellation."""
