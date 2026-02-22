"""
Model for metrics curves: buffers for x and y per metric. Append-only, used by dashboard.
"""

from __future__ import annotations

from collections import deque

# Keys we plot (losses + optional gpu_mem)
PLOT_KEYS = ("box_loss", "cls_loss", "dfl_loss")
MAX_POINTS = 5000  # keep last N points to avoid unbounded growth


class MetricsPlotModel:
    """Holds x (step) and y values for each metric. Step is incremented on each push."""

    def __init__(self, max_points: int = MAX_POINTS) -> None:
        self._max_points = max_points
        self._step = 0
        self._curves: dict[str, tuple[deque[float], deque[float]]] = {
            k: (deque(maxlen=max_points), deque(maxlen=max_points)) for k in PLOT_KEYS
        }

    def push(self, metrics: dict) -> bool:
        """
        Append one sample from metrics dict. Uses box_loss, cls_loss, dfl_loss.
        Returns True if any value was added.
        """
        added = False
        for key in PLOT_KEYS:
            v = metrics.get(key)
            if v is not None and isinstance(v, (int, float)):
                x_buf, y_buf = self._curves[key]
                x_buf.append(float(self._step))
                y_buf.append(float(v))
                added = True
        if added:
            self._step += 1
        return added

    def get_curve_data(self, key: str) -> tuple[list[float], list[float]]:
        """Return (x_list, y_list) for the given metric key."""
        if key not in self._curves:
            return [], []
        x_buf, y_buf = self._curves[key]
        return list(x_buf), list(y_buf)

    def get_all_curves(self) -> dict[str, tuple[list[float], list[float]]]:
        return {k: self.get_curve_data(k) for k in PLOT_KEYS}

    def clear(self) -> None:
        self._step = 0
        for x_buf, y_buf in self._curves.values():
            x_buf.clear()
            y_buf.clear()
