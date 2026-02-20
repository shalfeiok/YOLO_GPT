"""Infrastructure: application bootstrap, signals bridge, DI, settings.

Keep this package import lightweight: do not import Qt GUI modules at import time.
Some headless CI environments have PySide6 installed but miss runtime GUI libs
(e.g. ``libGL.so.1``). Lazy exports below allow importing
``app.ui.infrastructure.di`` without triggering Qt GUI initialization.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "create_application",
    "Container",
    "NotificationCenter",
    "install_error_boundary",
    "AppSettings",
    "TrainingSignals",
    "DetectionSignals",
]


def __getattr__(name: str) -> Any:
    if name == "create_application":
        return import_module("app.ui.infrastructure.application").create_application
    if name == "Container":
        return import_module("app.ui.infrastructure.di").Container
    if name == "NotificationCenter":
        return import_module("app.ui.infrastructure.notifications").NotificationCenter
    if name == "install_error_boundary":
        return import_module("app.ui.infrastructure.error_boundary").install_error_boundary
    if name == "AppSettings":
        return import_module("app.ui.infrastructure.settings").AppSettings
    if name == "TrainingSignals":
        return import_module("app.ui.infrastructure.signals").TrainingSignals
    if name == "DetectionSignals":
        return import_module("app.ui.infrastructure.signals").DetectionSignals
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
