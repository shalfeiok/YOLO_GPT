"""Integrations view facade."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.core.events import (
    JobCancelled,
    JobFailed,
    JobFinished,
    JobLogLine,
    JobProgress,
    JobRetrying,
    JobStarted,
    JobTimedOut,
)
from app.ui.views.integrations.view_model import IntegrationsViewModel
from app.ui.views.integrations.view_parts import (
    IntegrationsConfigActionsMixin,
    IntegrationsJobsMixin,
    IntegrationsLayoutMixin,
    IntegrationsToastMixin,
)

if TYPE_CHECKING:
    from app.ui.infrastructure.di import Container


class IntegrationsView(
    IntegrationsJobsMixin,
    IntegrationsLayoutMixin,
    IntegrationsToastMixin,
    IntegrationsConfigActionsMixin,
    QWidget,
):
    """Вкладка «Интеграции»: экспорт/импорт конфигурации, ссылки на документацию."""

    def __init__(self, container: Container | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._vm = IntegrationsViewModel(container)
        self._state = self._vm.load_state()
        self._current_job_id: str | None = None
        self._subs = []
        self._root_layout = QVBoxLayout(self)
        try:
            self._vm.state_changed.connect(self._on_state_changed)  # type: ignore[attr-defined]
        except Exception:
            import logging

            logging.getLogger(__name__).debug("Integrations view update failed", exc_info=True)
        if self._container:
            bus = self._container.event_bus
            for et in (
                JobStarted,
                JobProgress,
                JobFinished,
                JobFailed,
                JobCancelled,
                JobRetrying,
                JobTimedOut,
                JobLogLine,
            ):
                self._subs.append(bus.subscribe_weak(et, self._on_job_event))
        self._build_ui()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._container:
            bus = self._container.event_bus
            for s in self._subs:
                bus.unsubscribe(s)
        self._subs.clear()
        super().closeEvent(event)
