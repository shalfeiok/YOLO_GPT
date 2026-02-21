"""
QSettings wrapper: main window geometry, sidebar state, dock layout, theme.
"""
from __future__ import annotations

from typing import cast

from PySide6.QtCore import QByteArray, QSettings, QSize


class AppSettings:
    """Application and window persistence via QSettings (platform-specific path)."""

    def __init__(self) -> None:
        self._q = QSettings("YOLOStudio", "YOLO Desktop Studio")

    # --- Main window ---
    def get_main_window_geometry(self) -> QByteArray | None:
        return cast(QByteArray | None, self._q.value("mainWindow/geometry", None, QByteArray))

    def set_main_window_geometry(self, geometry: QByteArray) -> None:
        self._q.setValue("mainWindow/geometry", geometry)

    def get_main_window_state(self) -> QByteArray | None:
        return cast(QByteArray | None, self._q.value("mainWindow/state", None, QByteArray))

    def set_main_window_state(self, state: QByteArray) -> None:
        self._q.setValue("mainWindow/state", state)

    def get_main_window_size(self) -> QSize | None:
        return cast(QSize | None, self._q.value("mainWindow/size", None, QSize))

    def set_main_window_size(self, size: QSize) -> None:
        self._q.setValue("mainWindow/size", size)

    # --- Sidebar ---
    def get_sidebar_collapsed(self) -> bool:
        return bool(self._q.value("sidebar/collapsed", False, bool))

    def set_sidebar_collapsed(self, collapsed: bool) -> None:
        self._q.setValue("sidebar/collapsed", collapsed)

    # --- Theme ---
    def get_theme(self) -> str:
        return str(self._q.value("theme/name", "dark", str))  # "dark" | "light"

    def set_theme(self, name: str) -> None:
        self._q.setValue("theme/name", name)

    def sync(self) -> None:
        self._q.sync()
