"""Application port for creating frame sources (camera/video).

This allows UI/application code to depend on a small protocol instead of concrete
OpenCV classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True, slots=True)
class FrameSourceSpec:
    source: int | str


class FrameSource(Protocol):
    def is_opened(self) -> bool: ...

    def read(self) -> tuple[bool, np.ndarray | None]: ...

    def release(self) -> None: ...


class CapturePort(Protocol):
    def create_frame_source(self, spec: FrameSourceSpec) -> FrameSource: ...
