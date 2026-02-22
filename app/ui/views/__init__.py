from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from app.ui.views.detection.view import DetectionView as DetectionView
    from app.ui.views.training.view import TrainingView as TrainingView

__all__ = ["TrainingView", "DetectionView"]


def __getattr__(name: str):
    if name == "DetectionView":
        from app.ui.views.detection.view import DetectionView

        return DetectionView
    if name == "TrainingView":
        from app.ui.views.training.view import TrainingView

        return TrainingView
    raise AttributeError(name)
