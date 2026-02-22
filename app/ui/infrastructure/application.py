"""
QApplication setup: High DPI, organization and app name for QSettings.
"""

from __future__ import annotations

import sys
from typing import NoReturn

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication


def create_application() -> QApplication:
    """Create and configure QApplication. Call before any Qt widgets.
    High DPI: Qt 6 scales automatically on 4K/mixed-DPI; PassThrough keeps fractional scaling.
    """
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("YOLO Desktop Studio")
    app.setOrganizationName("YOLOStudio")
    app.setApplicationVersion("1.0")
    return app


def run_application(app: QApplication) -> NoReturn:
    """Run the event loop. Does not return until app quits."""
    sys.exit(app.exec() if hasattr(app, "exec") else app.exec_())
