"""
Command palette: Ctrl+K overlay to run actions by name (switch tab, theme, etc.).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from app.ui.theme.tokens import Tokens


class CommandItem:
    def __init__(self, id_: str, title: str, keywords: str = "") -> None:
        self.id = id_
        self.title = title
        self.keywords = (title + " " + keywords).strip().lower()


def _default_commands() -> list[CommandItem]:
    return [
        CommandItem("tab_training", "Перейти: Обучение", "training"),
        CommandItem("tab_detection", "Перейти: Детекция", "detection"),
        CommandItem("tab_datasets", "Перейти: Датасеты", "datasets"),
        CommandItem("tab_validation", "Перейти: Валидация", "validation"),
        CommandItem("tab_segmentation", "Перейти: Сегментация", "segmentation"),
        CommandItem("tab_pose", "Перейти: Поза", "pose"),
        CommandItem("tab_classification", "Перейти: Классификация", "classification"),
        CommandItem("tab_tracking", "Перейти: Трекинг", "tracking"),
        CommandItem("tab_autoannotation", "Перейти: Аннотация", "annotation auto"),
        CommandItem("tab_benchmark", "Перейти: Бенчмарк", "benchmark"),
        CommandItem("tab_experiments", "Перейти: Эксперименты", "experiments"),
        CommandItem("tab_integrations", "Перейти: Интеграции", "integrations"),
        CommandItem("tab_jobs", "Перейти: Задачи", "jobs background"),
        CommandItem("theme_light", "Тема: Светлая", "light"),
        CommandItem("theme_dark", "Тема: Тёмная", "dark"),
    ]


class CommandPalette(QDialog):
    """Modal overlay: type to filter, Enter to run selected command."""

    def __init__(self, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self._commands = _default_commands()
        self._filtered: list[CommandItem] = []
        self._on_run: Callable[[str], None] = lambda _id: None  # set by MainWindow
        self.setWindowTitle("Команды")
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setMinimumSize(400, 200)
        t = Tokens
        self.setStyleSheet(
            f"""
            QDialog {{ background: {t.surface}; border: 1px solid {t.border};
                       border-radius: {t.radius_md}px; }}
            QLineEdit {{ background: {t.surface_hover}; color: {t.text_primary};
                         border: none; border-radius: {t.radius_sm}px;
                         padding: 10px 12px; font-size: 14px; }}
            QListWidget {{ background: {t.surface}; color: {t.text_primary};
                           border: none; outline: none; }}
            QListWidget::item {{ padding: 8px 12px; }}
            QListWidget::item:selected {{ background: {t.primary}; color: white; }}
            QListWidget::item:hover {{ background: {t.surface_hover}; }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self._edit = QLineEdit()
        self._edit.setPlaceholderText("Введите команду…")
        self._edit.textChanged.connect(self._apply_filter)
        self._edit.returnPressed.connect(self._run_selected)
        layout.addWidget(self._edit)
        self._list = QListWidget()
        self._list.setMinimumWidth(360)
        self._list.setMaximumHeight(280)
        self._list.itemDoubleClicked.connect(lambda item: self._run_at_index(self._list.row(item)))
        self._list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self._list)
        self._apply_filter("")
        self._list.setCurrentRow(0)

    def set_on_run(self, callback: Callable[[str], None]) -> None:
        """Set callback(id: str) called when user selects a command."""
        self._on_run = callback

    def _apply_filter(self, text: str) -> None:
        q = text.strip().lower()
        if not q:
            self._filtered = list(self._commands)
        else:
            self._filtered = [c for c in self._commands if q in c.keywords]
        self._list.clear()
        for c in self._filtered:
            self._list.addItem(QListWidgetItem(c.title))
        if self._filtered:
            self._list.setCurrentRow(0)

    def _on_row_changed(self, row: int) -> None:
        pass

    def _run_at_index(self, index: int) -> None:
        if 0 <= index < len(self._filtered):
            self._on_run(self._filtered[index].id)
            self.accept()

    def _run_selected(self) -> None:
        row = self._list.currentRow()
        self._run_at_index(row)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            super().keyPressEvent(event)
            return
        super().keyPressEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if self.parentWidget():
            geo = self.geometry()
            parent_center = self.parentWidget().geometry().center()
            self.move(
                parent_center.x() - geo.width() // 2,
                parent_center.y() - geo.height() // 2 - 80,
            )
        self._edit.setFocus(Qt.FocusReason.OtherFocusReason)
        self._edit.clear()
        self._apply_filter("")
        if self._filtered:
            self._list.setCurrentRow(0)

    @staticmethod
    def run_id_to_tab(id_: str) -> str | None:
        """Map command id to TAB_IDS entry, or None."""
        m = {
            "tab_training": "training",
            "tab_detection": "detection",
            "tab_datasets": "datasets",
            "tab_validation": "validation",
            "tab_segmentation": "segmentation",
            "tab_pose": "pose",
            "tab_classification": "classification",
            "tab_tracking": "tracking",
            "tab_autoannotation": "autoannotation",
            "tab_benchmark": "benchmark",
            "tab_experiments": "experiments",
            "tab_integrations": "integrations",
            "tab_jobs": "jobs",
        }
        return m.get(id_)


def run_id_to_tab(id_: str) -> str | None:
    """Map command id to tab_id for MainWindow. Re-export of CommandPalette.run_id_to_tab."""
    return CommandPalette.run_id_to_tab(id_)
