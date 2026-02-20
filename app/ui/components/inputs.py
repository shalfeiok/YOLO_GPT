"""
Validated numeric input: min/max, tooltip, optional suffix. Uses theme.
NoWheelSpinBox: QSpinBox без изменения значения колёсиком мыши.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QSlider, QSpinBox, QWidget

from app.ui.theme.tokens import Tokens


class NoWheelSpinBox(QSpinBox):
    """SpinBox, игнорирующий колёсико мыши (только кнопки +/- и клавиатура)."""

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


class NoWheelSlider(QSlider):
    """Slider, игнорирующий колёсико мыши."""

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


class ValidatedSpinBox(NoWheelSpinBox):
    """SpinBox with theme styling, optional tooltip and validation range."""

    value_changed_int = Signal(int)  # emitted when value is valid and changed

    def __init__(
        self,
        parent: QWidget | None = None,
        min_val: int = 0,
        max_val: int = 9999,
        default: int = 0,
        tooltip: str = "",
    ) -> None:
        super().__init__(parent)
        t = Tokens
        self.setRange(min_val, max_val)
        self.setValue(default)
        if tooltip:
            self.setToolTip(tooltip)
        self.setMinimumHeight(32)
        self.setStyleSheet(
            f"""
            QSpinBox {{
                background-color: {t.surface};
                color: {t.text_primary};
                border: {t.border_width}px solid {t.border};
                border-radius: {t.radius_sm}px;
                padding: {t.space_xs}px {t.space_sm}px;
                min-width: 80px;
            }}
            QSpinBox:hover {{
                border-color: {t.text_secondary};
            }}
            QSpinBox:focus {{
                border-color: {t.primary};
            }}
            QSpinBox:disabled {{
                background-color: {t.surface_hover};
                color: {t.text_secondary};
            }}
            """
        )
        self.valueChanged.connect(self._emit_int)

    def _emit_int(self, value: int) -> None:
        self.value_changed_int.emit(value)

    def get_int(self) -> int:
        return int(self.value())
