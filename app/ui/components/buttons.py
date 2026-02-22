"""
Primary and secondary buttons. Styling from ThemeManager global stylesheet (#primaryButton, #secondaryButton).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QWidget


class PrimaryButton(QPushButton):
    """Main action button: accent background, hover. Uses app stylesheet."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("primaryButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(36)


class SecondaryButton(QPushButton):
    """Secondary action: surface background, border. Uses app stylesheet."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("secondaryButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(36)
