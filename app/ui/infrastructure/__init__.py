"""Infrastructure: application, signals bridge, DI, settings."""

from app.ui.infrastructure.application import create_application
from app.ui.infrastructure.di import Container
from app.ui.infrastructure.error_boundary import install_error_boundary
from app.ui.infrastructure.notifications import NotificationCenter
from app.ui.infrastructure.settings import AppSettings
from app.ui.infrastructure.signals import DetectionSignals, TrainingSignals

__all__ = [
    "create_application",
    "Container",
    "NotificationCenter",
    "install_error_boundary",
    "AppSettings",
    "TrainingSignals",
    "DetectionSignals",
]
