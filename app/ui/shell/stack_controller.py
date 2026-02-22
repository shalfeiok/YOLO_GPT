"""
Stack controller: QStackedWidget + lazy tab loading. Creates view only on first show.
"""

from __future__ import annotations

import logging
import traceback
from collections.abc import Callable

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.paths import get_app_state_dir
from app.ui.components.demo import create_components_demo_widget

log = logging.getLogger(__name__)

# Tab ids in order (must match sidebar order)
TAB_IDS = ("datasets", "training", "detection", "integrations", "jobs")


def _placeholder_widget(title: str, subtitle: str = "") -> QWidget:
    w = QLabel(f"{title}\n{subtitle}")
    w.setStyleSheet("font-size: 14px; color: #94a3b8; padding: 24px;")
    w.setWordWrap(True)
    return w


def _default_factory(tab_id: str) -> QWidget:
    titles = {
        "datasets": "Датасеты",
        "training": "Обучение",
        "detection": "Детекция",
        "integrations": "Интеграции и мониторинг",
        "jobs": "Задачи",
    }
    return _placeholder_widget(
        titles.get(tab_id, tab_id),
        f"Контент будет добавлен в Phase 4–5. (tab_id: {tab_id})",
    )


class ErrorWidget(QWidget):
    def __init__(self, tab_id: str, exc: BaseException, tb_text: str) -> None:
        super().__init__()
        self._traceback = tb_text
        root = QVBoxLayout(self)

        title = QLabel("Ошибка загрузки вкладки")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ef4444;")
        root.addWidget(title)

        summary = QLabel(f"{tab_id}: {type(exc).__name__}: {exc}")
        summary.setWordWrap(True)
        root.addWidget(summary)

        tb = QPlainTextEdit()
        tb.setReadOnly(True)
        tb.setPlainText(tb_text)
        tb.setMinimumHeight(180)
        root.addWidget(tb)

        copy_btn = QPushButton("Copy traceback")
        copy_btn.clicked.connect(self._copy_traceback)
        root.addWidget(copy_btn)

        logs_btn = QPushButton("Open logs folder")
        logs_btn.clicked.connect(self._open_logs_folder)
        root.addWidget(logs_btn)
        root.addStretch(1)

    def _copy_traceback(self) -> None:
        QApplication.clipboard().setText(self._traceback)

    def _open_logs_folder(self) -> None:
        logs_path = get_app_state_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs_path)))


class StackController:
    """Manages QStackedWidget and lazy-creates tab content on first switch."""

    def __init__(
        self,
        stack: QStackedWidget,
        factories: dict[str, Callable[[], QWidget]] | None = None,
    ) -> None:
        self._stack = stack
        self._factories = dict(factories) if factories else {}
        self._factories.setdefault("training", lambda: create_components_demo_widget())
        self._created: set[str] = set()
        self._pending_create: set[str] = set()

        for tab_id in TAB_IDS:
            placeholder = _placeholder_widget("Загрузка…", tab_id)
            placeholder.setObjectName(f"placeholder_{tab_id}")
            self._stack.addWidget(placeholder)

    def switch_to(self, tab_id: str) -> None:
        if tab_id not in TAB_IDS:
            return
        index = TAB_IDS.index(tab_id)
        if tab_id not in self._created:
            self._schedule_create(tab_id)
        self._stack.setCurrentIndex(index)

    def _schedule_create(self, tab_id: str) -> None:
        if tab_id in self._created or tab_id in self._pending_create:
            return
        self._pending_create.add(tab_id)

        def _create() -> None:
            self._pending_create.discard(tab_id)
            if tab_id in self._created:
                return
            index = TAB_IDS.index(tab_id)
            factory = self._factories.get(tab_id) or (lambda: _default_factory(tab_id))
            try:
                widget = factory()
            except Exception as exc:
                tb_text = traceback.format_exc()
                log.exception("Failed to create tab '%s'", tab_id)
                widget = ErrorWidget(tab_id=tab_id, exc=exc, tb_text=tb_text)
            old_widget = self._stack.widget(index)
            self._stack.removeWidget(old_widget)
            old_widget.deleteLater()
            self._stack.insertWidget(index, widget)
            self._created.add(tab_id)

        # Defer heavy tab construction to next event-loop tick so switching tabs
        # doesn't freeze UI on first open and the placeholder can render.
        QTimer.singleShot(0, _create)

    def tab_index(self, tab_id: str) -> int:
        if tab_id not in TAB_IDS:
            return 0
        return TAB_IDS.index(tab_id)
