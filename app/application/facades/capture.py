"""Capture facade.

Kept for backwards compatibility while we migrate the UI to application ports.
Prefer importing from :mod:`app.application.ports.capture` directly.
"""

from app.application.ports.capture import CapturePort, FrameSource, FrameSourceSpec

__all__ = [
    "CapturePort",
    "FrameSource",
    "FrameSourceSpec",
]
