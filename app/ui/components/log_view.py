"""
Log view: QListView + filter by level, smart auto-scroll, batched updates.
"""
from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme.tokens import Tokens
from app.ui.components.log_model import (
    LOG_LEVEL_ERROR,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARNING,
    LogListModel,
)

FILTER_ALL = "Все"
FILTER_INFO = "Info"
FILTER_WARNING = "Warning"
FILTER_ERROR = "Error"


class LogFilterProxy(QSortFilterProxyModel):
    """Filter by level. Accept rows where level matches the filter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._filter_level: str | None = None  # None = all

    def set_filter_level(self, level: str | None) -> None:
        self._filter_level = level
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: object) -> bool:
        if self._filter_level is None or self._filter_level == FILTER_ALL:
            return True
        src = self.sourceModel()
        if not isinstance(src, LogListModel):
            return True
        row_level = src.level_at(source_row)
        return row_level == self._filter_level


class LogView(QWidget):
    """ListView for log lines with level filter and auto-scroll when at bottom."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = LogListModel(self)
        self._proxy = LogFilterProxy(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterKeyColumn(0)
        self._list = QListView()
        self._list.setModel(self._proxy)
        self._list.setUniformItemSizes(True)
        self._list.setWordWrap(True)
        t = Tokens
        self._list.setStyleSheet(
            f"QListView {{ font-family: Consolas; font-size: 12px; background: {t.surface_hover}; "
            f"border-radius: {t.radius_sm}px; color: {t.text_primary}; }}"
        )
        self._list.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self._at_bottom = True
        self._list.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self._list.verticalScrollBar().rangeChanged.connect(self._on_range_changed)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Уровень:"))
        self._filter_combo = QComboBox()
        self._filter_combo.addItems([FILTER_ALL, FILTER_INFO, FILTER_WARNING, FILTER_ERROR])
        self._filter_combo.setStyleSheet(
            f"QComboBox {{ background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; "
            f"border-radius: {t.radius_sm}px; padding: 4px; min-height: 24px; }}"
        )
        self._filter_combo.currentTextChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._filter_combo)
        filter_row.addStretch()
        layout.addLayout(filter_row)
        layout.addWidget(self._list)

    def _on_filter_changed(self, text: str) -> None:
        level_map = {
            FILTER_ALL: None,
            FILTER_INFO: LOG_LEVEL_INFO,
            FILTER_WARNING: LOG_LEVEL_WARNING,
            FILTER_ERROR: LOG_LEVEL_ERROR,
        }
        self._proxy.set_filter_level(level_map.get(text))

    def _on_scroll(self, value: int) -> None:
        bar = self._list.verticalScrollBar()
        self._at_bottom = value >= bar.maximum()

    def _on_range_changed(self, _min: int, _max: int) -> None:
        if self._at_bottom:
            self._list.scrollToBottom()

    def append_line(self, line: str, level: str | None = None) -> None:
        self._model.append_line(line, level)
        if self._at_bottom:
            self._list.scrollToBottom()

    def append_batch(self, lines: list[tuple[str, str | None]]) -> None:
        self._model.append_batch(lines)
        if self._at_bottom:
            self._list.scrollToBottom()

    def clear(self) -> None:
        self._model.clear()

    def refresh_theme(self) -> None:
        """Re-apply theme-dependent styles (called when theme changes)."""
        t = Tokens
        self._list.setStyleSheet(
            f"QListView {{ font-family: Consolas; font-size: 12px; background: {t.surface_hover}; "
            f"border-radius: {t.radius_sm}px; color: {t.text_primary}; }}"
        )
        self._filter_combo.setStyleSheet(
            f"QComboBox {{ background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; "
            f"border-radius: {t.radius_sm}px; padding: 4px; min-height: 24px; }}"
        )

