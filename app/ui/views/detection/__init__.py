from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .view import DetectionView as DetectionView

__all__ = ["DetectionView"]


def __getattr__(name: str):
    if name == "DetectionView":
        from .view import DetectionView
        return DetectionView
    raise AttributeError(name)
