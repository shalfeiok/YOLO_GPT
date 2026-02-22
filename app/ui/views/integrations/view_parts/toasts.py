from __future__ import annotations

from PySide6.QtWidgets import QMessageBox


class IntegrationsToastMixin:
    def _toast_ok(self, title: str, message: str) -> None:
        if self._container and self._container.notifications:
            self._container.notifications.success(title, message)
            return
        QMessageBox.information(self, title, message)

    def _toast_warn(self, title: str, message: str) -> None:
        if self._container and self._container.notifications:
            self._container.notifications.warning(title, message)
            return
        QMessageBox.warning(self, title, message)

    def _toast_err(self, title: str, message: str) -> None:
        if self._container and self._container.notifications:
            self._container.notifications.error(title, message)
            return
        QMessageBox.critical(self, title, message)
