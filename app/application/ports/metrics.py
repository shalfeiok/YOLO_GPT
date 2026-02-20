"""Application port for system metrics.

The UI should depend on this interface instead of importing infrastructure
implementations (psutil/pynvml/subprocess) directly.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol


class MetricsPort(Protocol):
    def get_cpu_percent(self) -> float:
        """CPU usage 0-100."""

    def get_memory_info(self) -> tuple[float, float]:
        """Return (used_gb, total_gb)."""

    def get_gpu_info(self) -> Optional[dict[str, Any]]:
        """GPU metrics for display; None if not available."""
