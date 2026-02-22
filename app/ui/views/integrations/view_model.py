"""Integrations ViewModel facade with mixin-based decomposition."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.application.ports.integrations import IntegrationsPort
from app.core.jobs import JobHandle, ProcessJobHandle
from app.ui.views.integrations.view_model_parts import IntegrationsActionsMixin, IntegrationsConfigMixin

try:  # Optional in headless test environments.
    from PySide6.QtCore import QObject, Signal
except Exception:  # pragma: no cover

    class QObject:  # type: ignore[no-redef]
        pass

    class Signal:  # type: ignore[no-redef]
        def __init__(self, *_: object, **__: object) -> None:
            pass

        def emit(self, *_: object, **__: object) -> None:
            return

if TYPE_CHECKING:
    from app.ui.infrastructure.di import Container


class IntegrationsViewModel(IntegrationsConfigMixin, IntegrationsActionsMixin, QObject):
    """Application-facing API for the Integrations view."""

    state_changed = Signal(object)

    def __init__(self, container: Container | None = None) -> None:
        super().__init__()
        self._container = container
        self._integrations: IntegrationsPort | None = None
        self._jobs: dict[str, JobHandle[Any] | ProcessJobHandle[Any]] = {}

    @property
    def integrations(self) -> IntegrationsPort:
        if self._integrations is None:
            if self._container is None:
                raise RuntimeError("Container is required for integrations operations")
            self._integrations = self._container.integrations
        return self._integrations
