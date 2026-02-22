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
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import PREVIEW_MAX_SIZE

COCO_SKELETON = [
    (5, 7),
    (7, 9),
    (6, 8),
    (8, 10),
    (5, 6),
    (5, 11),
    (6, 12),
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
]


class PoseWorker(QThread):
    frame_ready = Signal(object, float)
    failed = Signal(str)

    def __init__(self, cfg: dict):
        super().__init__()
        self._cfg = cfg
        self._run = True

    def stop(self):
        self._run = False

    def run(self):
        try:
            from ultralytics import YOLO

            model = YOLO(self._cfg["weights"])
            cap = cv2.VideoCapture(0 if self._cfg["source"] != "Video File" else self._cfg["video"])
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
                    task="pose",
                    device=self._cfg["device"],
                    verbose=False,
                )
                out = frame.copy()
                if res and res[0].keypoints is not None:
                    if self._cfg["render_mode"] == "Стандартная (Ultralytics)":
                        out = res[0].plot()
                    else:
                        kxy = (
                            res[0].keypoints.xy.cpu().numpy()
                            if hasattr(res[0].keypoints.xy, "cpu")
                            else res[0].keypoints.xy
                        )
                        kcf = (
                            res[0].keypoints.conf.cpu().numpy()
                            if hasattr(res[0].keypoints.conf, "cpu")
                            else res[0].keypoints.conf
                        )
                        for pi, pts in enumerate(kxy):
                            confs = kcf[pi]
                            if self._cfg["show_points"]:
                                for i, (x, y) in enumerate(pts):
                                    c = float(confs[i]) if i < len(confs) else 0
                                    if c >= self._cfg["kpt_conf"]:
                                        cv2.circle(
                                            out,
                                            (int(x), int(y)),
                                            3,
                                            (0, int(255 * c), 255 - int(255 * c)),
                                            -1,
                                        )
                            if self._cfg["show_skeleton"]:
                                for a, b in COCO_SKELETON:
                                    if (
                                        a < len(pts)
                                        and b < len(pts)
                                        and confs[a] >= self._cfg["kpt_conf"]
                                        and confs[b] >= self._cfg["kpt_conf"]
                                    ):
                                        cv2.line(
                                            out,
                                            tuple(pts[a].astype(int)),
                                            tuple(pts[b].astype(int)),
                                            (0, 255, 0),
                                            2,
                                        )
                fps = 1.0 / max(1e-6, (time.perf_counter() - t0))
                self.frame_ready.emit(out, fps)
            cap.release()
        except Exception as e:
            self.failed.emit(str(e))


class PoseView(QWidget):
    def __init__(self, _container) -> None:
        super().__init__()
        self._w = None
        self._ui()

    def _ui(self):
        root = QVBoxLayout(self)
        g = QGroupBox("Оценка позы")
        f = QFormLayout(g)

        self._weights = QLineEdit("weights/yolo11n-pose.pt")
        self._weights.setToolTip("Путь к pose-весам")
        bw = QPushButton("…")
        bw.clicked.connect(self._pick_w)
        wr = QHBoxLayout()
        wr.addWidget(self._weights, 1)
        wr.addWidget(bw)
        ww = QWidget()
        ww.setLayout(wr)
        f.addRow("Веса:", ww)

        self._source = QComboBox()
        self._source.addItems(["Full Screen", "Window", "Camera", "Video File"])
        f.addRow("Источник:", self._source)

        self._video = QLineEdit("")
        self._video.setPlaceholderText("Путь к видео")
        bv = QPushButton("…")
        bv.clicked.connect(self._pick_v)
        vr = QHBoxLayout()
        vr.addWidget(self._video, 1)
        vr.addWidget(bv)
        vw = QWidget()
        vw.setLayout(vr)
        f.addRow("Видео:", vw)

        self._device = QComboBox()
        self._device.addItems(["cpu", "cuda:0"])
        f.addRow("Устройство:", self._device)

        self._render = QComboBox()
        self._render.addItems(["Кастомная", "Стандартная (Ultralytics)"])
        f.addRow("Отрисовка:", self._render)

        self._conf = QDoubleSpinBox()
        self._conf.setRange(0, 1)
        self._conf.setSingleStep(0.01)
        self._conf.setValue(0.25)

        self._kpt_conf = QDoubleSpinBox()
        self._kpt_conf.setRange(0, 1)
        self._kpt_conf.setSingleStep(0.01)
        self._kpt_conf.setValue(0.5)

        self._sk = QCheckBox("Показывать скелет")
        self._sk.setChecked(True)
        self._pts = QCheckBox("Показывать точки")
        self._pts.setChecked(True)
        self._bbox = QCheckBox("Показывать bbox")
        f.addRow("Conf:", self._conf)
        f.addRow("Kpt conf:", self._kpt_conf)
        f.addRow(self._sk)
        f.addRow(self._pts)
        f.addRow(self._bbox)
        root.addWidget(g)

        self._btn = QPushButton("Старт / Стоп")
        self._btn.clicked.connect(self._toggle)
        root.addWidget(self._btn)
        self._fps = QLabel("FPS: 0")
        root.addWidget(self._fps)
        self._prev = QLabel("Preview")
        self._prev.setMinimumSize(*PREVIEW_MAX_SIZE)
        root.addWidget(self._prev, 1)

    def _pick_w(self):
        p, _ = QFileDialog.getOpenFileName(self, "weights", "", "*.pt")
        if p:
            self._weights.setText(p)

    def _pick_v(self):
        p, _ = QFileDialog.getOpenFileName(self, "video", "", "Video (*.mp4 *.avi *.mkv)")
        if p:
            self._video.setText(p)

    def _toggle(self):
        if self._w and self._w.isRunning():
            self._w.stop()
            self._w.wait()
            return
        if not Path(self._weights.text()).exists():
            QMessageBox.warning(self, "Ошибка", "Выберите веса")
            return
        self._w = PoseWorker(
            {
                "weights": self._weights.text(),
                "source": self._source.currentText(),
                "video": self._video.text(),
                "device": self._device.currentText(),
                "render_mode": self._render.currentText(),
                "conf": self._conf.value(),
                "kpt_conf": self._kpt_conf.value(),
                "show_skeleton": self._sk.isChecked(),
                "show_points": self._pts.isChecked(),
            }
        )
        self._w.frame_ready.connect(self._on_frame)
        self._w.failed.connect(lambda e: QMessageBox.critical(self, "Ошибка", e))
        self._w.start()

    def _on_frame(self, frame, fps):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        img = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        self._prev.setPixmap(
            QPixmap.fromImage(img).scaled(*PREVIEW_MAX_SIZE, Qt.AspectRatioMode.KeepAspectRatio)
        )
        self._fps.setText(f"FPS: {fps:.1f}")
