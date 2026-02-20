"""
Card container: parameter panels, sections. Uses theme tokens.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget


class Card(QFrame):
    """Frame with surface background, border, radius. Styling from app stylesheet (#card)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from app.ui.theme.tokens import Tokens
        t = Tokens
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(t.card_padding, t.card_padding, t.card_padding, t.card_padding)
        self._layout.setSpacing(t.space_md)

    def layout(self) -> QVBoxLayout:
        return self._layout
