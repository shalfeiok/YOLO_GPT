from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtWidgets import QWidget

from app.ui.components.theme import Tokens
from app.ui.views.integrations.view_model import IntegrationsViewModel


def edit_style() -> str:
    t = Tokens
    return (
        f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; "
        f"border-radius: {t.radius_sm}px; padding: 6px;"
    )


@dataclass(slots=True)
class SectionsCtx:
    parent: QWidget
    vm: IntegrationsViewModel
    state: object
    toast_ok: Callable[[str, str], None]
    toast_err: Callable[[str, str], None]
