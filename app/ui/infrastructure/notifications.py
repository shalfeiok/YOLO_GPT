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
        return

    @staticmethod
    def _join_message(title_or_message: str, message: str | None = None) -> str:
        if message is None:
            return title_or_message
        return f"{title_or_message}: {message}" if title_or_message else message

    def info(self, title_or_message: str, message: str | None = None) -> None:
        self._status(self._join_message(title_or_message, message))

    def success(self, title_or_message: str, message: str | None = None) -> None:
        self._status(self._join_message(title_or_message, message))

    def warning(self, title_or_message: str, message: str | None = None) -> None:
        self._status(self._join_message(title_or_message, message))

    def error(self, title_or_message: str, message: str | None = None) -> None:
        text = self._join_message(title_or_message, message)
        self._status(text)
        if QMessageBox is None:
            return
        try:
            QMessageBox.critical(self._window, "Ошибка", text)
        except Exception:
            return

    # Backward-compatible API used in older views.
    def notify_info(self, message: str) -> None:
        self.info(message)

    def notify_success(self, message: str) -> None:
        self.success(message)

    def notify_warning(self, message: str) -> None:
        self.warning(message)

    def notify_error(self, message: str) -> None:
        self.error(message)
