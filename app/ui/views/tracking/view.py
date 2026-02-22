from __future__ import annotations

import csv
import time
from collections import defaultdict, deque
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFileDialog, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget

from app.config import PREVIEW_MAX_SIZE


class TrackWorker(QThread):
    frame_ready = Signal(object, float, int, int)
    failed = Signal(str)

    def __init__(self, cfg):
        super().__init__(); self._cfg = cfg; self._run = True; self.tracks = []

    def stop(self): self._run = False

    def run(self):
        try:
            from ultralytics import YOLO

            model = YOLO(self._cfg["weights"])
            cap = cv2.VideoCapture(0 if self._cfg["source"] == "Camera" else self._cfg["video"])
            hist = defaultdict(lambda: deque(maxlen=self._cfg["hist_len"]))
            seen = set(); frame_id = 0
            while self._run and cap.isOpened():
                ok, frame = cap.read(); frame_id += 1
                if not ok: break
                t0 = time.perf_counter()
                results = model.track(frame, persist=True, conf=self._cfg["conf"], iou=self._cfg["iou"], tracker=("botsort.yaml" if self._cfg["tracker"] == "BoT-SORT" else "bytetrack.yaml"), verbose=False)
                out = frame.copy(); active = 0
                if results:
                    r = results[0]
                    boxes = r.boxes
                    if boxes is not None and boxes.id is not None:
                        bxy = boxes.xyxy.cpu().numpy(); bids = boxes.id.int().cpu().tolist(); cls = boxes.cls.int().cpu().tolist(); cfs = boxes.conf.cpu().numpy().tolist()
                        active = len(bids)
                        for i, tid in enumerate(bids):
                            x1, y1, x2, y2 = map(int, bxy[i])
                            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                            hist[tid].append((cx, cy)); seen.add(tid)
                            self.tracks.append([frame_id, tid, x1, y1, x2, y2, cls[i], cfs[i]])
                            if self._cfg["show_bbox"]: cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            if self._cfg["show_id"]: cv2.putText(out, f"ID {tid}", (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                            if self._cfg["show_tail"] and len(hist[tid]) > 1:
                                cv2.polylines(out, [np.array(hist[tid], dtype=np.int32)], False, (255, 0, 0), 2)
                fps = 1 / max(1e-6, time.perf_counter() - t0)
                self.frame_ready.emit(out, fps, active, len(seen))
            cap.release()
        except Exception as e:
            self.failed.emit(str(e))


class TrackingView(QWidget):
    def __init__(self, _container) -> None:
        super().__init__(); self._w = None; self._ui()

    def _ui(self):
        root = QVBoxLayout(self)
        g = QGroupBox("Трекинг"); f = QFormLayout(g)
        self._weights = QLineEdit(); bw = QPushButton("…"); bw.clicked.connect(self._pick_w)
        wr = QHBoxLayout(); wr.addWidget(self._weights, 1); wr.addWidget(bw); ww = QWidget(); ww.setLayout(wr); f.addRow("Веса:", ww)
        self._src = QComboBox(); self._src.addItems(["Camera", "Video File"]); f.addRow("Источник:", self._src)
        self._video = QLineEdit(); bv = QPushButton("…"); bv.clicked.connect(self._pick_v)
        vr = QHBoxLayout(); vr.addWidget(self._video, 1); vr.addWidget(bv); vw = QWidget(); vw.setLayout(vr); f.addRow("Видео:", vw)
        self._tracker = QComboBox(); self._tracker.addItems(["BoT-SORT", "ByteTrack"]); f.addRow("Трекер:", self._tracker)
        self._conf = QDoubleSpinBox(); self._conf.setRange(0, 1); self._conf.setValue(0.25)
        self._iou = QDoubleSpinBox(); self._iou.setRange(0, 1); self._iou.setValue(0.45)
        self._hist = QSpinBox(); self._hist.setRange(1, 300); self._hist.setValue(30)
        self._tail = QCheckBox("Показывать хвосты треков"); self._tail.setChecked(True)
        self._id = QCheckBox("Показывать ID"); self._id.setChecked(True)
        self._bbox = QCheckBox("Показывать bbox"); self._bbox.setChecked(True)
        f.addRow("Conf:", self._conf); f.addRow("IOU:", self._iou); f.addRow("Track history:", self._hist)
        f.addRow(self._tail); f.addRow(self._id); f.addRow(self._bbox)
        root.addWidget(g)
        self._btn = QPushButton("Старт / Стоп"); self._btn.clicked.connect(self._toggle); root.addWidget(self._btn)
        stat = QHBoxLayout(); self._active = QLabel("Активных: 0"); self._uniq = QLabel("Уникальных ID: 0"); self._fps = QLabel("FPS: 0")
        stat.addWidget(self._active); stat.addWidget(self._uniq); stat.addWidget(self._fps); root.addLayout(stat)
        self._preview = QLabel(); root.addWidget(self._preview, 1)
        self._export = QPushButton("Экспорт треков"); self._export.clicked.connect(self._export_csv); root.addWidget(self._export)

    def _pick_w(self):
        p, _ = QFileDialog.getOpenFileName(self, "weights", "", "*.pt")
        if p: self._weights.setText(p)

    def _pick_v(self):
        p, _ = QFileDialog.getOpenFileName(self, "video", "", "Video (*.mp4 *.avi *.mkv)")
        if p: self._video.setText(p)

    def _toggle(self):
        if self._w and self._w.isRunning(): self._w.stop(); self._w.wait(); return
        if not Path(self._weights.text()).exists(): QMessageBox.warning(self, "Ошибка", "Выберите веса"); return
        cfg = {"weights": self._weights.text(), "source": self._src.currentText(), "video": self._video.text(), "tracker": self._tracker.currentText(), "conf": self._conf.value(), "iou": self._iou.value(), "hist_len": self._hist.value(), "show_tail": self._tail.isChecked(), "show_id": self._id.isChecked(), "show_bbox": self._bbox.isChecked()}
        self._w = TrackWorker(cfg); self._w.frame_ready.connect(self._on_frame); self._w.failed.connect(lambda e: QMessageBox.critical(self, "Ошибка", e)); self._w.start()

    def _on_frame(self, frame, fps, active, uniq):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); h, w, _ = rgb.shape
        img = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        self._preview.setPixmap(QPixmap.fromImage(img).scaled(*PREVIEW_MAX_SIZE, Qt.AspectRatioMode.KeepAspectRatio))
        self._active.setText(f"Активных: {active}"); self._uniq.setText(f"Уникальных ID: {uniq}"); self._fps.setText(f"FPS: {fps:.1f}")

    def _export_csv(self):
        if not self._w: return
        p, _ = QFileDialog.getSaveFileName(self, "tracks", "tracks.csv", "CSV (*.csv)")
        if not p: return
        with open(p, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f); wr.writerow(["frame_id", "track_id", "x1", "y1", "x2", "y2", "class", "confidence"]); wr.writerows(self._w.tracks)
