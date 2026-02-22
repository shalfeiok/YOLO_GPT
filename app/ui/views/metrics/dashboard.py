"""
Metrics dashboard: PyQtGraph plot with streaming loss curves, zoom/pan, crosshair, hover values.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from app.ui.components.buttons import SecondaryButton
from app.ui.theme.tokens import Tokens
from app.ui.views.metrics.plot_model import PLOT_KEYS, MetricsPlotModel

try:
    import pyqtgraph as pg
    from pyqtgraph import InfiniteLine, PlotDataItem, PlotWidget

    _HAS_PYQTGRAPH = True
except ImportError:
    _HAS_PYQTGRAPH = False
    PlotWidget = None
    PlotDataItem = None
    InfiniteLine = None


# Throttle curve redraws for smooth 20–30 FPS during training
METRICS_REFRESH_MS = 100

# Curve colors (theme-aligned)
CURVE_COLORS = {
    "box_loss": "#3b82f6",
    "cls_loss": "#22c55e",
    "dfl_loss": "#eab308",
}


class MetricsDashboardWidget(QWidget):
    """Live loss curves: box_loss, cls_loss, dfl_loss. Zoom, pan, crosshair, hover value."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = MetricsPlotModel()
        self._curves: dict[str, PlotDataItem] = {}
        self._vline: InfiniteLine | None = None
        self._hline: InfiniteLine | None = None
        self._label: pg.TextItem | None = None
        self._plot_widget: PlotWidget | None = None
        self._pending_refresh = False
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._on_refresh_tick)
        self._refresh_timer.setInterval(METRICS_REFRESH_MS)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if not _HAS_PYQTGRAPH:
            from PySide6.QtWidgets import QLabel

            layout.addWidget(QLabel("Установите pyqtgraph для графиков метрик."))
            self._curves = {}
            return
        self._build_plot()

    def _build_plot(self) -> None:
        t = Tokens
        pg.setConfigOptions(
            background=t.surface,
            foreground=t.text_primary,
            antialias=True,
        )
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._plot_widget.setMinimumHeight(220)
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.setLabel("left", "Loss")
        self._plot_widget.setLabel("bottom", "Step")
        # Default: left drag = pan, right drag = rect zoom (pyqtgraph default)
        for key in PLOT_KEYS:
            color = CURVE_COLORS.get(key, t.primary)
            curve = pg.PlotDataItem(pen=pg.mkPen(color, width=2), name=key)
            self._plot_widget.addItem(curve)
            self._curves[key] = curve
        self._vline = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(t.text_secondary, width=1, style=Qt.PenStyle.DashLine),
        )
        self._hline = pg.InfiniteLine(
            angle=0,
            movable=False,
            pen=pg.mkPen(t.text_secondary, width=1, style=Qt.PenStyle.DashLine),
        )
        self._plot_widget.addItem(self._vline, ignoreBounds=True)
        self._plot_widget.addItem(self._hline, ignoreBounds=True)
        self._label = pg.TextItem(
            "", anchor=(0, 1), color=t.text_primary, fill=pg.mkColor(t.surface)
        )
        self._plot_widget.addItem(self._label, ignoreBounds=True)
        self._label.setZValue(100)
        self._plot_widget.getViewBox().scene().sigMouseMoved.connect(self._on_mouse_moved)
        self.layout().addWidget(self._plot_widget)
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 4, 0, 0)
        export_btn = SecondaryButton("Экспорт CSV…")
        export_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(export_btn)
        btn_layout.addStretch()
        self.layout().addWidget(btn_row)

    def _on_mouse_moved(self, pos) -> None:
        if self._plot_widget is None or self._vline is None or self._label is None:
            return
        # Help mypy: these attributes are optional.
        assert self._hline is not None
        vb = self._plot_widget.getViewBox()
        if vb.sceneBoundingRect().contains(pos):
            mouse_point = vb.mapSceneToView(pos)
            self._vline.setPos(mouse_point.x())
            self._hline.setPos(mouse_point.y())
            x_val = mouse_point.x()
            y_val = mouse_point.y()
            nearest = None
            nearest_dist = float("inf")
            for key in PLOT_KEYS:
                x_buf, y_buf = self._model.get_curve_data(key)
                if not x_buf:
                    continue
                for i, (x, y) in enumerate(zip(x_buf, y_buf)):
                    d = (x - x_val) ** 2 + (y - y_val) ** 2
                    if d < nearest_dist:
                        nearest_dist = d
                        nearest = (key, x, y)
            if nearest:
                key, x, y = nearest
                self._label.setText(f"{key}: {y:.4f}")
                self._label.setPos(x, y)
            self._label.setVisible(True)
        else:
            self._label.setVisible(False)

    def _on_refresh_tick(self) -> None:
        if self._pending_refresh:
            self._pending_refresh = False
            self._refresh_timer.stop()
            self._refresh_curves()

    def push_metrics(self, metrics: dict) -> None:
        """Append one sample; curve redraw is throttled to METRICS_REFRESH_MS for smooth FPS."""
        if not _HAS_PYQTGRAPH or not self._curves:
            return
        if not self._model.push(metrics):
            return
        self._pending_refresh = True
        if not self._refresh_timer.isActive():
            self._refresh_timer.start()

    def _refresh_curves(self) -> None:
        if not _HAS_PYQTGRAPH or not self._curves:
            return
        for key in PLOT_KEYS:
            x_list, y_list = self._model.get_curve_data(key)
            if x_list and y_list:
                self._curves[key].setData(x_list, y_list)

    def clear(self) -> None:
        """Reset all curves (e.g. when starting a new training run)."""
        self._pending_refresh = False
        self._refresh_timer.stop()
        self._model.clear()
        self._refresh_curves()

    def refresh_theme(self) -> None:
        """Re-apply theme colors to plot (called when theme changes)."""
        if not _HAS_PYQTGRAPH or not self._plot_widget:
            return
        t = Tokens
        pg.setConfigOptions(background=t.surface, foreground=t.text_primary, antialias=True)
        self._plot_widget.getViewBox().setBackgroundColor(pg.mkColor(t.surface))
        for key in PLOT_KEYS:
            color = CURVE_COLORS.get(key, t.primary)
            self._curves[key].setPen(pg.mkPen(color, width=2))
        if self._vline and self._hline:
            pen = pg.mkPen(t.text_secondary, width=1, style=Qt.PenStyle.DashLine)
            self._vline.setPen(pen)
            self._hline.setPen(pen)
        if self._label:
            self._label.setColor(pg.mkColor(t.text_primary))
            self._label.fill = pg.mkBrush(pg.mkColor(t.surface))

    def _export_csv(self) -> None:
        """Save curve data to CSV. Uses longest curve for step count."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт метрик", "", "CSV (*.csv);;Все файлы (*.*)"
        )
        if not path:
            return
        data = self._model.get_all_curves()
        max_len = max(len(x) for x, _ in data.values()) if data else 0
        if max_len == 0:
            return
        lines = ["step," + ",".join(PLOT_KEYS)]
        for i in range(max_len):
            row = [str(i)]
            for key in PLOT_KEYS:
                x_list, y_list = data[key]
                row.append(str(y_list[i]) if i < len(y_list) else "")
            lines.append(",".join(row))
        Path(path).write_text("\n".join(lines), encoding="utf-8")
