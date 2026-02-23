from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ui.views.training.view import TrainingView
    from app.ui.views.training.view_model import TrainingViewModel

__all__ = ["TrainingView", "TrainingViewModel"]
