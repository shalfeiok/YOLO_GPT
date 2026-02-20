from __future__ import annotations

from app.ui.theme.tokens import Tokens


def edit_style() -> str:
    """Единый стиль для полей ввода/комбо/спинов в диалогах настроек."""
    t = Tokens
    return (
        "QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {"
        f"  padding: 6px 8px; border-radius: 8px; border: 1px solid {t.border};"
        f"  background: {t.surface}; color: {t.text_primary};"
        "}"
        "QComboBox::drop-down { border: none; width: 28px; }"
        "QComboBox QAbstractItemView {"
        f"  background: {t.surface}; color: {t.text_primary};"
        f"  border: 1px solid {t.border}; selection-background-color: {t.surface_hover};"
        "}"
    )
