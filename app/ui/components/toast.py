"""
Toast notification: show message, auto-hide after delay. Non-modal overlay.
"""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from app.ui.theme.tokens import Tokens


def show_toast(
    parent: QWidget,
    message: str,
    duration_ms: int = 3000,
    style: str = "info",
) -> None:
    """
    Show a toast over parent. style: "info" | "success" | "warning" | "error".
    """
    t = Tokens
    colors = {
        "info": (t.primary, t.text_primary),
        "success": (t.success, "white"),
        "warning": (t.warning, "black"),
        "error": (t.error, "white"),
    }
    bg, fg = colors.get(style, colors["info"])

    label = QLabel(message, parent)
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet(
        f"""
        background-color: {bg};
        color: {fg};
        border-radius: {t.radius_md}px;
        padding: {t.space_md}px {t.space_lg}px;
        font-weight: 500;
        """
    )
    label.setGraphicsEffect(QGraphicsOpacityEffect(label))
    label.graphicsEffect().setOpacity(0.0)
    label.adjustSize()
    # Center in parent
    x = (parent.width() - label.width()) // 2
    y = parent.height() - label.height() - t.space_xl * 4
    label.setGeometry(max(0, x), max(0, y), label.width() + t.space_lg, label.height() + t.space_sm)
    label.show()
    label.raise_()

    effect = label.graphicsEffect()

    anim_in = QPropertyAnimation(effect, b"opacity")
    anim_in.setDuration(200)
    anim_in.setStartValue(0.0)
    anim_in.setEndValue(1.0)
    anim_in.start()

    def fade_out() -> None:
        anim_out = QPropertyAnimation(effect, b"opacity")
        anim_out.setDuration(250)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)
        anim_out.finished.connect(label.deleteLater)
        anim_out.start()

    QTimer.singleShot(duration_ms, fade_out)
