"""UI composition container.

Keeps UI-only collaborators (theme manager, notifications) outside of the
application container to preserve layer boundaries.
"""

from __future__ import annotations

from app.application.container import Container as AppContainer


class Container(AppContainer):
    def __init__(self) -> None:
        super().__init__()
        self.theme_manager = None
        self.notifications = None


__all__ = ["Container"]
