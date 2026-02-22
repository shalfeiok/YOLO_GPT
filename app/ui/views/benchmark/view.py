from __future__ import annotations

import csv
import time
from pathlib import Path

import numpy as np
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class BenchmarkView(QWidget):
    def __init__(self, _container) -> None:
        super().__init__()
        self._rows = []
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        g = QGroupBox("Бенчмаркинг")
        f = QFormLayout(g)

        self._w = QLineEdit("weights/yolo11n.pt")
        self._w.setToolTip("Путь к .pt весам модели")
        bw = QPushButton("…")
        bw.setToolTip("Выбрать веса")
        bw.clicked.connect(self._pick_w)
        wr = QHBoxLayout()
        wr.addWidget(self._w, 1)
        wr.addWidget(bw)
        ww = QWidget()
        ww.setLayout(wr)
        f.addRow("Веса:", ww)

        self._device = QComboBox()
        self._device.addItems(["cpu", "cuda:0"])
        self._device.setToolTip("Устройство выполнения")
        f.addRow("Устройство:", self._device)

        self._imgsz = QSpinBox()
        self._imgsz.setRange(64, 2048)
        self._imgsz.setValue(640)
        self._imgsz.setToolTip("Размер изображения для теста")
        f.addRow("Image size:", self._imgsz)

        self._pt = QCheckBox("PyTorch (.pt)")
        self._pt.setChecked(True)
        self._pt.setEnabled(False)
        self._onnx = QCheckBox("ONNX")
        self._ov = QCheckBox("OpenVINO")
        self._trt = QCheckBox("TensorRT")
        self._ts = QCheckBox("TorchScript")
        self._onnx.setToolTip("Экспорт и тест ONNX")
        self._ov.setToolTip("Экспорт и тест OpenVINO")
        self._trt.setToolTip("Экспорт и тест TensorRT")
        self._ts.setToolTip("Экспорт и тест TorchScript")
        for c in [self._pt, self._onnx, self._ov, self._trt, self._ts]:
            f.addRow(c)
        root.addWidget(g)

        self._run = QPushButton("Запустить бенчмарк")
        self._run.clicked.connect(self._run_bench)
        root.addWidget(self._run)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Format", "FPS", "Latency (ms)", "File Size (MB)", "Status"]
        )
        root.addWidget(self._table, 1)

        self._exp = QPushButton("Экспорт таблицы CSV")
        self._exp.clicked.connect(self._exp_csv)
        root.addWidget(self._exp)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        root.addWidget(self._log, 1)

    def _pick_w(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "weights", "", "*.pt")
        if p:
            self._w.setText(p)

    def _run_bench(self) -> None:
        try:
            from ultralytics import YOLO

            weights = Path(self._w.text().strip())
            if not weights.exists():
                QMessageBox.warning(self, "Ошибка", "Укажите существующий файл весов")
                return

            model = YOLO(str(weights))
            device = self._device.currentText()
            formats = ["pt"]
            if self._onnx.isChecked():
                formats.append("onnx")
            if self._ov.isChecked():
                formats.append("openvino")
            if self._trt.isChecked():
                formats.append("engine")
            if self._ts.isChecked():
                formats.append("torchscript")

            self._rows = []
            self._log.clear()
            for fmt in formats:
                self._log.append(f"Testing {fmt} on {device}")
                path = weights
                status = "ok"
                if fmt != "pt":
                    try:
                        out = model.export(format=fmt, imgsz=self._imgsz.value(), device=device)
                        path = Path(out)
                    except Exception as e:
                        self._rows.append([fmt, 0.0, 0.0, 0.0, f"export fail: {e}"])
                        continue

                x = np.random.randint(
                    0,
                    255,
                    (self._imgsz.value(), self._imgsz.value(), 3),
                    dtype=np.uint8,
                )
                t0 = time.perf_counter()
                for _ in range(100):
                    model.predict(x, imgsz=self._imgsz.value(), device=device, verbose=False)
                dt = (time.perf_counter() - t0) / 100
                fps = 1 / max(1e-6, dt)
                size_mb = path.stat().st_size / 1024 / 1024 if path.exists() else 0.0
                self._rows.append([fmt, fps, dt * 1000, size_mb, status])
            self._render()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _render(self) -> None:
        self._table.setRowCount(len(self._rows))
        best = max([r[1] for r in self._rows], default=0.0)
        for i, r in enumerate(self._rows):
            for j, v in enumerate(r):
                it = QTableWidgetItem(f"{v:.3f}" if isinstance(v, float) else str(v))
                if j == 1 and float(r[1]) == best and best > 0:
                    it.setBackground(QColor("#14532d"))
                self._table.setItem(i, j, it)

    def _exp_csv(self) -> None:
        p, _ = QFileDialog.getSaveFileName(self, "csv", "benchmark.csv", "CSV (*.csv)")
        if not p:
            return
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Format", "FPS", "Latency (ms)", "File Size (MB)", "Status"])
            w.writerows(self._rows)
