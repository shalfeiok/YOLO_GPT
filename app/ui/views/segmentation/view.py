from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
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
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.config import PREVIEW_MAX_SIZE


class SegWorker(QThread):
    frame_ready = Signal(object, float)
    failed = Signal(str)

    def __init__(self, cfg: dict):
        super().__init__()
        self._cfg = cfg
        self._run = True

    def stop(self) -> None:
        self._run = False

    def _source(self):
        src = self._cfg["source"]
        if src == "Camera":
            return cv2.VideoCapture(0)
        if src == "Video File":
            return cv2.VideoCapture(self._cfg["video"])
        return cv2.VideoCapture(0)

    def run(self) -> None:
        try:
            from ultralytics import YOLO

            model = YOLO(self._cfg["weights"])
            cap = self._source()
            if not cap.isOpened():
                raise RuntimeError("Не удалось открыть источник видео.")
            while self._run and cap.isOpened():
                ok, frame = cap.read()
                if not ok:
                    break
                t0 = time.perf_counter()
                res = model.predict(
                    frame,
                    conf=self._cfg["conf"],
                    iou=self._cfg["iou"],
                    task="segment",
                    device=self._cfg["device"],
                    verbose=False,
                )
                out = frame.copy()
                if res:
                    if self._cfg["render_mode"] == "Стандартная (Ultralytics)":
                        out = res[0].plot()
                    elif res[0].masks is not None and len(res[0].masks.xy):
                        for poly in res[0].masks.xy:
                            pts = np.array(poly, dtype=np.int32)
                            if self._cfg["show_masks"]:
                                overlay = out.copy()
                                cv2.fillPoly(overlay, [pts], (0, 255, 0))
                                out = cv2.addWeighted(
                                    overlay,
                                    self._cfg["alpha"],
                                    out,
                                    1.0 - self._cfg["alpha"],
                                    0,
                                )
                            if self._cfg["show_contours"]:
                                cv2.polylines(out, [pts], True, (255, 255, 0), 2)
                fps = 1.0 / max(1e-6, (time.perf_counter() - t0))
                self.frame_ready.emit(out, fps)
            cap.release()
        except Exception as e:
            self.failed.emit(str(e))


class SegmentationView(QWidget):
    def __init__(self, _container) -> None:
        super().__init__()
        self._worker: SegWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        g = QGroupBox("Сегментация")
        f = QFormLayout(g)

        self._weights = QLineEdit("weights/yolo11n-seg.pt")
        self._weights.setToolTip("Путь к весам сегментации")
        b = QPushButton("…")
        b.clicked.connect(self._pick_weights)
        row = QHBoxLayout()
        row.addWidget(self._weights, 1)
        row.addWidget(b)
        w = QWidget()
        w.setLayout(row)
        f.addRow("Веса:", w)

        self._source = QComboBox()
        self._source.addItems(["Full Screen", "Window", "Camera", "Video File"])
        self._source.setToolTip("Источник для инференса")
        f.addRow("Источник:", self._source)

        self._video = QLineEdit("")
        self._video.setPlaceholderText("Путь к видео")
        bv = QPushButton("…")
        bv.clicked.connect(self._pick_video)
        vr = QHBoxLayout()
        vr.addWidget(self._video, 1)
        vr.addWidget(bv)
        vw = QWidget()
        vw.setLayout(vr)
        f.addRow("Видео:", vw)

        self._device = QComboBox()
        self._device.addItems(["cpu", "cuda:0"])
        self._device.setToolTip("Устройство инференса")
        f.addRow("Устройство:", self._device)

        self._render = QComboBox()
        self._render.addItems(["Кастомная", "Стандартная (Ultralytics)"])
        self._render.setToolTip("Режим отрисовки результата")
        f.addRow("Отрисовка:", self._render)

        self._conf = QSlider()
        self._conf.setOrientation(Qt.Orientation.Horizontal)
        self._conf.setRange(1, 100)
        self._conf.setValue(25)
        self._iou = QSlider()
        self._iou.setOrientation(Qt.Orientation.Horizontal)
        self._iou.setRange(1, 100)
        self._iou.setValue(45)
        f.addRow("Confidence:", self._conf)
        f.addRow("IOU:", self._iou)

        self._masks = QCheckBox("Показывать маски")
        self._masks.setChecked(True)
        self._contours = QCheckBox("Показывать контуры")
        self._bbox = QCheckBox("Показывать bounding boxes")
        self._alpha = QSlider()
        self._alpha.setOrientation(Qt.Orientation.Horizontal)
        self._alpha.setRange(10, 90)
        self._alpha.setValue(40)
        f.addRow(self._masks)
        f.addRow(self._contours)
        f.addRow(self._bbox)
        f.addRow("Alpha:", self._alpha)
        root.addWidget(g)

        self._start = QPushButton("Старт / Стоп")
        self._start.clicked.connect(self._toggle)
        root.addWidget(self._start)
        self._fps = QLabel("FPS: 0")
        root.addWidget(self._fps)
        self._preview = QLabel("Preview")
        self._preview.setMinimumSize(*PREVIEW_MAX_SIZE)
        self._preview.setScaledContents(True)
        root.addWidget(self._preview, 1)

    def _pick_weights(self):
        p, _ = QFileDialog.getOpenFileName(self, "weights", "", "*.pt")
        if p:
            self._weights.setText(p)

    def _pick_video(self):
        p, _ = QFileDialog.getOpenFileName(self, "video", "", "Video (*.mp4 *.avi *.mkv)")
        if p:
            self._video.setText(p)

    def _toggle(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait()
            return
        if not Path(self._weights.text()).exists():
            QMessageBox.warning(self, "Ошибка", "Укажите веса")
            return
        cfg = {
            "weights": self._weights.text().strip(),
            "source": self._source.currentText(),
            "video": self._video.text().strip(),
            "device": self._device.currentText(),
            "render_mode": self._render.currentText(),
            "conf": self._conf.value() / 100,
            "iou": self._iou.value() / 100,
            "show_masks": self._masks.isChecked(),
            "show_contours": self._contours.isChecked(),
            "alpha": self._alpha.value() / 100,
        }
        self._worker = SegWorker(cfg)
        self._worker.frame_ready.connect(self._on_frame)
        self._worker.failed.connect(lambda e: QMessageBox.critical(self, "Ошибка", e))
        self._worker.start()

    def _on_frame(self, frame: np.ndarray, fps: float):
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        self._preview.setPixmap(QPixmap.fromImage(img).scaled(*PREVIEW_MAX_SIZE))
        self._fps.setText(f"FPS: {fps:.1f}")
