"""Application port for model detection.

The UI should not depend on concrete detector implementations.
It should request a detector via this port and interact through the IDetector
interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.interfaces import IDetector
from app.features.detection_visualization.domain import is_onnx_family


@dataclass(frozen=True, slots=True)
class DetectorSpec:
    """Describes which detector engine to use."""

    engine: str  # "pytorch" | "onnx"


class DetectionPort(Protocol):
    """Factory/locator for detectors."""

    def get_detector(self, spec: DetectorSpec) -> IDetector:
        ...

    def get_for_visualization_backend(self, backend_id: str) -> IDetector:
        """Pick detector based on visualization backend (e.g. ONNX family)."""

        ...


def detector_spec_for_backend(backend_id: str) -> DetectorSpec:
    return DetectorSpec(engine="onnx" if is_onnx_family(backend_id) else "pytorch")
