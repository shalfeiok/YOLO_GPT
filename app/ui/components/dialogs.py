"""
Confirmation and other dialogs. Blocking modal.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QMessageBox, QWidget


def confirm_dialog(
    parent: QWidget,
    title: str,
    message: str,
    ok_text: str = "Да",
    cancel_text: str = "Отмена",
    on_accept: Callable[[], None] | None = None,
    on_reject: Callable[[], None] | None = None,
) -> bool:
    """
    Show Yes/No dialog. Returns True if user accepted.
    Optionally call on_accept/on_reject after close.
    """
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(message)
    box.setIcon(QMessageBox.Icon.Question)
    box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
    box.setDefaultButton(QMessageBox.StandardButton.Cancel)
    box.button(QMessageBox.StandardButton.Ok).setText(ok_text)
    box.button(QMessageBox.StandardButton.Cancel).setText(cancel_text)
    result = box.exec()
    accepted = QMessageBox.StandardButton(result) == QMessageBox.StandardButton.Ok
    if accepted and on_accept:
        on_accept()
    if not accepted and on_reject:
        on_reject()
    return accepted


def confirm_stop_training(parent: QWidget, on_confirm: Callable[[], None]) -> None:
    """Ask «Остановить обучение?» and call on_confirm if user confirms."""
    confirm_dialog(
        parent,
        "Остановить обучение?",
        "Обучение будет прервано. Продолжить?",
        ok_text="Остановить",
        cancel_text="Отмена",
        on_accept=on_confirm,
    )
