"""
ThemeManager: dark/light token sets, runtime switch, QPalette and application stylesheet.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from app.ui.theme.tokens import DARK, LIGHT, TokenSet, apply_token_set

if TYPE_CHECKING:
    from app.ui.infrastructure.settings import AppSettings

THEME_DARK = "dark"
THEME_LIGHT = "light"


class ThemeManager(QObject):
    """
    Manages current theme: tokens, QPalette, global stylesheet; emits theme_changed.
    Part 4.11: No global singleton; inject via Container (DI).
    """

    theme_changed = Signal(str)  # theme name

    def __init__(self, settings: AppSettings | None = None) -> None:
        super().__init__()
        self._settings = settings
        self._current = THEME_DARK

    def get_theme(self) -> str:
        return self._current

    def set_theme(self, name: str) -> None:
        if name not in (THEME_DARK, THEME_LIGHT):
            name = THEME_DARK
        if name == self._current:
            return
        self._current = name
        source = LIGHT if name == THEME_LIGHT else DARK
        apply_token_set(source)
        self._apply_palette(source)
        self._apply_stylesheet(source)
        if self._settings:
            self._settings.set_theme(name)
            self._settings.sync()
        self.theme_changed.emit(name)

    def tokens(self) -> TokenSet:
        """Current token set (same object as theme.tokens.Tokens, already updated)."""
        from app.ui.theme.tokens import Tokens

        return Tokens

    def _apply_palette(self, t: TokenSet) -> None:
        app = QApplication.instance()
        if not app:
            return
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, QColor(t.background_main))
        pal.setColor(QPalette.ColorRole.Base, QColor(t.surface))
        pal.setColor(QPalette.ColorRole.Button, QColor(t.surface_hover))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(t.text_primary))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor(t.text_primary))
        pal.setColor(QPalette.ColorRole.Text, QColor(t.text_primary))
        pal.setColor(QPalette.ColorRole.Highlight, QColor(t.primary))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(t.text_secondary))
        app.setPalette(pal)

    def _apply_stylesheet(self, t: TokenSet) -> None:
        app = QApplication.instance()
        if not app:
            return
        sheet = _build_application_stylesheet(t)
        app.setStyleSheet(sheet)


def _build_application_stylesheet(t: TokenSet) -> str:
    """Single global stylesheet so all screens update when theme changes."""
    return f"""
        QWidget, QMainWindow {{
            background-color: {t.background_main};
            color: {t.text_primary};
        }}
        QGroupBox {{
            font-weight: bold;
            color: {t.text_primary};
        }}
        QLineEdit, QComboBox {{
            background-color: {t.surface};
            color: {t.text_primary};
            border: 1px solid {t.border};
            border-radius: {t.radius_sm}px;
            padding: 4px 6px;
            min-height: 24px;
        }}
        QSpinBox {{
            background-color: {t.surface};
            color: {t.text_primary};
            border: 1px solid {t.border};
            border-radius: {t.radius_sm}px;
            padding: 4px 6px;
            min-height: 24px;
            min-width: 80px;
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 16px;
            border-left: 1px solid {t.border};
            background: {t.surface_hover};
        }}
        QSpinBox::down-button {{
            subcontrol-position: bottom right;
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background: {t.border};
        }}
        QPushButton {{
            background-color: {t.surface_hover};
            color: {t.text_primary};
            border: {t.border_width}px solid {t.border};
            border-radius: {t.radius_md}px;
            padding: {t.space_sm}px {t.space_lg}px;
            min-height: 36px;
        }}
        QPushButton:hover {{
            background-color: {t.border};
        }}
        #primaryButton {{
            background-color: {t.primary};
            color: white;
            border: none;
            border-radius: {t.radius_md}px;
            padding: {t.space_sm}px {t.space_lg}px;
            font-weight: 600;
        }}
        #primaryButton:hover {{
            background-color: {t.primary_hover};
        }}
        #primaryButton:disabled {{
            background-color: {t.surface_hover};
            color: {t.text_secondary};
        }}
        #secondaryButton {{
            background-color: {t.surface_hover};
            color: {t.text_primary};
            border: {t.border_width}px solid {t.border};
            border-radius: {t.radius_md}px;
            padding: {t.space_sm}px {t.space_lg}px;
        }}
        #secondaryButton:hover {{
            background-color: {t.border};
        }}
        #secondaryButton:disabled {{
            color: {t.text_secondary};
        }}
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QProgressBar {{
            border: 1px solid {t.border};
            border-radius: {t.radius_sm}px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background: {t.primary};
            border-radius: 4px;
        }}
        QListView {{
            font-family: Consolas;
            font-size: 12px;
            background: {t.surface_hover};
            border-radius: {t.radius_sm}px;
            color: {t.text_primary};
        }}
        QPlainTextEdit {{
            background: {t.surface_hover};
            color: {t.text_primary};
            border-radius: {t.radius_sm}px;
        }}
        QLabel {{
            color: {t.text_primary};
        }}
        #card {{
            background-color: {t.surface};
            border: {t.border_width}px solid {t.border};
            border-radius: {t.radius_lg}px;
        }}
    """
