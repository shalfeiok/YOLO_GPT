from __future__ import annotations

import csv
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget, QComboBox


class ClassificationView(QWidget):
    def __init__(self, container) -> None:
        super().__init__(); self._container = container; self._rows = []; self._build()

    def _build(self):
        root = QVBoxLayout(self)
        tabs = QTabWidget(); root.addWidget(tabs)
        one = QWidget(); ol = QVBoxLayout(one)
        g = QGroupBox("Одно изображение"); f = QFormLayout(g)
        self._img = QLineEdit(); bi = QPushButton("…"); bi.clicked.connect(self._pick_img)
        ir = QHBoxLayout(); ir.addWidget(self._img, 1); ir.addWidget(bi); iw = QWidget(); iw.setLayout(ir); f.addRow("Изображение:", iw)
        self._weights = QLineEdit(); bw = QPushButton("…"); bw.clicked.connect(self._pick_weights)
        wr = QHBoxLayout(); wr.addWidget(self._weights, 1); wr.addWidget(bw); ww = QWidget(); ww.setLayout(wr); f.addRow("Веса:", ww)
        ol.addWidget(g)
        self._preview = QLabel(); self._preview.setMinimumHeight(240); self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ol.addWidget(self._preview)
        self._btn = QPushButton("Классифицировать"); self._btn.clicked.connect(self._classify_one); ol.addWidget(self._btn)
        self._lat = QLabel("Время инференса: - мс"); ol.addWidget(self._lat)
        self._top5 = [QProgressBar() for _ in range(5)]
        for p in self._top5: ol.addWidget(p)
        tabs.addTab(one, "Одно изображение")

        batch = QWidget(); bl = QVBoxLayout(batch)
        gb = QGroupBox("Папка"); fb = QFormLayout(gb)
        self._folder = QLineEdit(); bf = QPushButton("…"); bf.clicked.connect(self._pick_folder)
        fr = QHBoxLayout(); fr.addWidget(self._folder, 1); fr.addWidget(bf); fw = QWidget(); fw.setLayout(fr); fb.addRow("Папка:", fw)
        self._bweights = QLineEdit(); bbw = QPushButton("…"); bbw.clicked.connect(self._pick_bweights)
        bwr = QHBoxLayout(); bwr.addWidget(self._bweights, 1); bwr.addWidget(bbw); bww = QWidget(); bww.setLayout(bwr); fb.addRow("Веса:", bww)
        bl.addWidget(gb)
        self._run_batch = QPushButton("Запустить batch"); self._run_batch.clicked.connect(self._run_folder); bl.addWidget(self._run_batch)
        self._prog = QProgressBar(); bl.addWidget(self._prog)
        self._filter = QComboBox(); self._filter.currentIndexChanged.connect(self._apply_filter); bl.addWidget(self._filter)
        self._table = QTableWidget(0, 5); self._table.setHorizontalHeaderLabels(["filename", "top1", "conf", "top2", "top3"]); bl.addWidget(self._table, 1)
        self._exp = QPushButton("Экспорт CSV"); self._exp.clicked.connect(self._export_csv); bl.addWidget(self._exp)
        tabs.addTab(batch, "Папка")

    def _pick_img(self):
        p, _ = QFileDialog.getOpenFileName(self, "img", "", "Images (*.jpg *.jpeg *.png *.bmp)")
        if p: self._img.setText(p); self._preview.setPixmap(QPixmap(p).scaledToHeight(220))

    def _pick_weights(self):
        p, _ = QFileDialog.getOpenFileName(self, "weights", "", "*.pt")
        if p: self._weights.setText(p)

    def _classify_one(self):
        try:
            from ultralytics import YOLO

            t0 = time.perf_counter()
            res = YOLO(self._weights.text()).predict(self._img.text(), task="classify", verbose=False)
            dt = (time.perf_counter() - t0) * 1000
            self._lat.setText(f"Время инференса: {dt:.2f} мс")
            probs = res[0].probs
            top = probs.top5
            conf = probs.top5conf
            for i in range(5):
                idx = int(top[i])
                p = float(conf[i]) * 100
                name = res[0].names.get(idx, str(idx))
                self._top5[i].setValue(int(p)); self._top5[i].setFormat(f"{name}: {p:.2f}%")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _pick_folder(self):
        p = QFileDialog.getExistingDirectory(self, "folder", "")
        if p: self._folder.setText(p)

    def _pick_bweights(self): self._pick_weights(); self._bweights.setText(self._weights.text())

    def _run_folder(self):
        try:
            from ultralytics import YOLO

            model = YOLO(self._bweights.text())
            files = [p for p in Path(self._folder.text()).iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}]
            self._rows = []
            self._prog.setValue(0)
            for i, f in enumerate(files, 1):
                r = model.predict(str(f), task="classify", verbose=False)[0]
                top = [r.names[int(x)] for x in r.probs.top5[:3]]
                conf = float(r.probs.top1conf)
                self._rows.append([f.name, top[0], conf, top[1], top[2]])
                self._prog.setValue(int(i / max(1, len(files)) * 100))
            classes = sorted({r[1] for r in self._rows})
            self._filter.clear(); self._filter.addItem("Все"); self._filter.addItems(classes)
            self._render_rows(self._rows)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _render_rows(self, rows):
        self._table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, v in enumerate(r):
                self._table.setItem(i, j, QTableWidgetItem(f"{v:.4f}" if isinstance(v, float) else str(v)))

    def _apply_filter(self):
        c = self._filter.currentText()
        if c == "Все": self._render_rows(self._rows)
        else: self._render_rows([r for r in self._rows if r[1] == c])

    def _export_csv(self):
        p, _ = QFileDialog.getSaveFileName(self, "csv", "classification.csv", "CSV (*.csv)")
        if not p: return
        with open(p, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f); wr.writerow(["filename", "top1", "confidence", "top2", "top3"]); wr.writerows(self._rows)
