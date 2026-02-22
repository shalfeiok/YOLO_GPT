"""
Skeleton loader: placeholder with shimmer for loading states.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QWidget

from app.ui.theme.tokens import Tokens


class SkeletonLoader(QFrame):
    """Rectangular placeholder with optional animated shimmer. Use while content loads."""

    def __init__(self, parent: QWidget | None = None, height: int = 48) -> None:
        super().__init__(parent)
        t = Tokens
        self.setFixedHeight(height)
        self.setObjectName("skeleton")
        self.setStyleSheet(
            f"""
            #skeleton {{
                background-color: {t.surface_hover};
                border-radius: {t.radius_sm}px;
            }}
            """
        )
        self._shimmer_pos = 0.0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_shimmer)

    def start_animation(self) -> None:
        self._anim_timer.start(50)

    def stop_animation(self) -> None:
        self._anim_timer.stop()

    def _tick_shimmer(self) -> None:
        self._shimmer_pos = (self._shimmer_pos + 0.05) % 1.0
        self.update()
