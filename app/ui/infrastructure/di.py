"""UI-facing import for the DI container.

The actual composition root lives in :mod:`app.application.container`.
This module remains as a compatibility shim to avoid changing many UI imports
at once.
"""

from __future__ import annotations

from app.application.container import Container

__all__ = ["Container"]
