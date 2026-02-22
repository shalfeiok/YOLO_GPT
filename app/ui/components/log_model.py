"""
Log list model: QAbstractListModel with level + text, max buffer, thread-safe append.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

LOG_LEVEL_INFO = "info"
LOG_LEVEL_WARNING = "warning"
LOG_LEVEL_ERROR = "error"

LEVELS = (LOG_LEVEL_INFO, LOG_LEVEL_WARNING, LOG_LEVEL_ERROR)

MAX_LOG_LINES = 100_000


def _infer_level(line: str) -> str:
    lower = line.lower()
    if "error" in lower or "exception" in lower or "traceback" in lower:
        return LOG_LEVEL_ERROR
    if "warn" in lower or "warning" in lower:
        return LOG_LEVEL_WARNING
    return LOG_LEVEL_INFO


class LogListModel(QAbstractListModel):
    """List model for log lines: (level, text). Max MAX_LOG_LINES, oldest dropped."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._entries: deque[tuple[str, str]] = deque(maxlen=MAX_LOG_LINES)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._entries)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or index.row() < 0 or index.row() >= len(self._entries):
            return None
        level, text = self._entries[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return text
        if role == Qt.ItemDataRole.UserRole:
            return level
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            int(Qt.ItemDataRole.DisplayRole): b"display",
            int(Qt.ItemDataRole.UserRole): b"level",
        }

    def append_line(self, line: str, level: str | None = None) -> None:
        """Append one line. Level inferred from content if not given."""
        if level is None:
            level = _infer_level(line)
        was_full = len(self._entries) == self._entries.maxlen
        self._entries.append((level, line))
        if was_full:
            self.beginRemoveRows(QModelIndex(), 0, 0)
            self.endRemoveRows()
        self.beginInsertRows(QModelIndex(), len(self._entries) - 1, len(self._entries) - 1)
        self.endInsertRows()

    def append_batch(self, lines: list[tuple[str, str | None]]) -> None:
        """Append multiple (line, level|None). One notify to avoid flicker."""
        if not lines:
            return
        maxlen = self._entries.maxlen
        new_entries = [
            (lvl if lvl is not None else _infer_level(line), line) for line, lvl in lines
        ]
        # deque.maxlen is Optional[int]; None means unbounded.
        if maxlen is None or len(self._entries) + len(new_entries) <= maxlen:
            start = len(self._entries)
            self._entries.extend(new_entries)
            self.beginInsertRows(QModelIndex(), start, len(self._entries) - 1)
            self.endInsertRows()
        else:
            combined = list(self._entries) + new_entries
            if maxlen is not None and len(combined) > maxlen:
                combined = combined[-maxlen:]
            self.beginResetModel()
            self._entries = deque(combined, maxlen=maxlen)
            self.endResetModel()

    def clear(self) -> None:
        self.beginResetModel()
        self._entries.clear()
        self.endResetModel()

    def level_at(self, row: int) -> str:
        if 0 <= row < len(self._entries):
            return self._entries[row][0]
        return LOG_LEVEL_INFO
