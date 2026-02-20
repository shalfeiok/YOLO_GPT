from __future__ import annotations

from dataclasses import dataclass

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMessageBox
except Exception:  # pragma: no cover
    QTimer = None  # type: ignore[assignment]
    QMessageBox = None  # type: ignore[assignment]


@dataclass(frozen=True)
class Notification:
    level: str
    message: str


class NotificationCenter:
    """Very small notification helper.

    In Qt we keep it intentionally minimal: show a short status message if possible,
    and fall back to QMessageBox for errors.
    """

    def __init__(self, window) -> None:
        self._window = window

    def _status(self, text: str, *, ms: int = 4500) -> None:
        try:
            sb = getattr(self._window, "statusBar", None)
            if callable(sb):
                sb = sb()
            if sb is not None and hasattr(sb, "showMessage"):
                sb.showMessage(text, ms)
                return
        except Exception:
            import logging
            logging.getLogger(__name__).debug('Notification display failed', exc_info=True)
        # If no status bar is available, do nothing (silent).
        return

    def info(self, message: str) -> None:
        self._status(message)

    def success(self, message: str) -> None:
        self._status(message)

    def warning(self, message: str) -> None:
        self._status(message)

    def error(self, message: str) -> None:
        self._status(message)
        if QMessageBox is None:
            return
        try:
            QMessageBox.critical(self._window, "Ошибка", message)
        except Exception:
            return
