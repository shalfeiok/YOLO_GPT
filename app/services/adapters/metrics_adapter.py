from __future__ import annotations

from typing import Any

from app.application.ports.metrics import MetricsPort


class MetricsAdapter(MetricsPort):
    """Infrastructure-backed implementation of MetricsPort."""

    def get_cpu_percent(self) -> float:
        from app.services.system_metrics import get_cpu_percent

        return get_cpu_percent()

    def get_memory_info(self) -> tuple[float, float]:
        from app.services.system_metrics import get_memory_info

        return get_memory_info()

    def get_gpu_info(self) -> dict[str, Any] | None:
        from app.services.system_metrics import get_gpu_info

        return get_gpu_info()
