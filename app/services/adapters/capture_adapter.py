"""Infrastructure adapter implementing CapturePort."""

from __future__ import annotations

from app.application.ports.capture import CapturePort, FrameSource, FrameSourceSpec
from app.services.capture_service import OpenCVFrameSource


class CaptureAdapter(CapturePort):
    def create_frame_source(self, spec: FrameSourceSpec) -> FrameSource:
        return OpenCVFrameSource(spec.source)
