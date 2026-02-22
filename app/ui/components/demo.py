"""
Demo widget: Card, Primary/Secondary buttons, ValidatedSpinBox, Toast, confirm dialog.
Used as placeholder content for Training tab until Phase 4.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.ui.components.buttons import PrimaryButton, SecondaryButton
from app.ui.components.cards import Card
from app.ui.components.dialogs import confirm_stop_training
from app.ui.components.inputs import ValidatedSpinBox
from app.ui.components.toast import show_toast
from app.ui.theme.tokens import Tokens


def create_components_demo_widget(parent: QWidget | None = None) -> QWidget:
    """Build a demo page with Card, buttons, spinbox, toast and confirm dialog."""
    container = QWidget(parent)
    layout = QVBoxLayout(container)
    layout.setSpacing(Tokens.space_lg)

    title = QLabel("Библиотека компонентов (Phase 3)")
    title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Tokens.text_primary};")
    layout.addWidget(title)

    card = Card(container)
    card.layout().addWidget(QLabel("Карточка с кнопками и полем"))
    row1 = QWidget()
    row1_layout = QVBoxLayout(row1)
    row1_layout.setContentsMargins(0, 0, 0, 0)
    spin = ValidatedSpinBox(row1, min_val=1, max_val=100, default=50, tooltip="Число от 1 до 100")
    row1_layout.addWidget(spin)
    card.layout().addWidget(row1)
    btn_row = QWidget()
    btn_layout = QVBoxLayout(btn_row)
    btn_layout.setContentsMargins(0, 0, 0, 0)
    btn_primary = PrimaryButton("Основная кнопка", btn_row)
    btn_secondary = SecondaryButton("Вторичная кнопка", btn_row)
    btn_layout.addWidget(btn_primary)
    btn_layout.addWidget(btn_secondary)
    card.layout().addWidget(btn_row)
    layout.addWidget(card)

    def on_toast() -> None:
        show_toast(container.window(), "Тост: компоненты готовы к Phase 4.", 2500, "success")

    def on_confirm() -> None:
        confirm_stop_training(
            container.window(),
            lambda: show_toast(container.window(), "Обучение остановлено (демо).", 1500),
        )

    btn_toast = PrimaryButton("Показать тост", container)
    btn_toast.clicked.connect(on_toast)
    layout.addWidget(btn_toast)
    btn_confirm = SecondaryButton("Диалог «Остановить обучение?»", container)
    btn_confirm.clicked.connect(on_confirm)
    layout.addWidget(btn_confirm)

    layout.addStretch()
    return container
