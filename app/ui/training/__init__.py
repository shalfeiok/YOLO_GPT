"""Training tab: constants, helpers, and UI (SOLID: Single Responsibility)."""
from app.ui.training.constants import (
    CONSOLE_MAX_LINES,
    MAX_DATASETS,
    METRICS_HEADERS_RU,
    METRICS_TOOLTIP_RU_BASE,
    METRICS_UPDATE_MS,
)
from app.ui.training.helpers import scan_trained_weights

__all__ = [
    "CONSOLE_MAX_LINES",
    "MAX_DATASETS",
    "METRICS_HEADERS_RU",
    "METRICS_TOOLTIP_RU_BASE",
    "METRICS_UPDATE_MS",
    "scan_trained_weights",
]
