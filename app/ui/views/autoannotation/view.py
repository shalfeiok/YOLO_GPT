from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

from PySide6.QtWidgets import QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton, QComboBox, QDoubleSpinBox, QCheckBox, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget


class AutoAnnotationView(QWidget):
    def __init__(self, container) -> None:
        super().__init__(); self._container = container; self._rows = []; self._stats = {}; self._build()

    def _build(self):
        root = QVBoxLayout(self)
        g = QGroupBox("Автоаннотирование"); f = QFormLayout(g)
        self._inp = QLineEdit(); bi = QPushButton("…"); bi.clicked.connect(self._pick_inp)
        ir = QHBoxLayout(); ir.addWidget(self._inp, 1); ir.addWidget(bi); iw = QWidget(); iw.setLayout(ir); f.addRow("Input:", iw)
        self._out = QLineEdit(); bo = QPushButton("…"); bo.clicked.connect(self._pick_out)
        orr = QHBoxLayout(); orr.addWidget(self._out, 1); orr.addWidget(bo); ow = QWidget(); ow.setLayout(orr); f.addRow("Output:", ow)
        self._w = QLineEdit(); bw = QPushButton("…"); bw.clicked.connect(self._pick_w)
        wr = QHBoxLayout(); wr.addWidget(self._w, 1); wr.addWidget(bw); ww = QWidget(); ww.setLayout(wr); f.addRow("Weights:", ww)
        self._conf = QDoubleSpinBox(); self._conf.setRange(0, 1); self._conf.setValue(0.25)
        self._iou = QDoubleSpinBox(); self._iou.setRange(0, 1); self._iou.setValue(0.45)
        self._only = QCheckBox("Сохранять только уверенные")
        self._fmt = QComboBox(); self._fmt.addItems(["YOLO TXT", "COCO JSON", "Pascal VOC XML"])
        f.addRow("Conf:", self._conf); f.addRow("IOU:", self._iou); f.addRow(self._only); f.addRow("Формат:", self._fmt)
        root.addWidget(g)
        self._run = QPushButton("Запустить аннотирование"); self._run.clicked.connect(self._run_job); root.addWidget(self._run)
        self._prog = QProgressBar(); root.addWidget(self._prog)
        self._table = QTableWidget(0, 3); self._table.setHorizontalHeaderLabels(["filename", "objects_found", "classes"]); root.addWidget(self._table, 1)
        self._open = QPushButton("Открыть папку результатов"); self._open.clicked.connect(self._open_dir); root.addWidget(self._open)
        self._log = QTextEdit(); self._log.setReadOnly(True); root.addWidget(self._log, 1)
        self._st = QLabel("Статистика: -"); root.addWidget(self._st)

    def _pick_inp(self):
        p = QFileDialog.getExistingDirectory(self, "input", "")
        if p: self._inp.setText(p); self._out.setText(str(Path(p).parent / f"{Path(p).name}_ann"))

    def _pick_out(self):
        p = QFileDialog.getExistingDirectory(self, "output", "")
        if p: self._out.setText(p)

    def _pick_w(self):
        p, _ = QFileDialog.getOpenFileName(self, "weights", "", "*.pt")
        if p: self._w.setText(p)

    def _run_job(self):
        try:
            from ultralytics import YOLO

            inp = Path(self._inp.text()); out = Path(self._out.text()); out.mkdir(parents=True, exist_ok=True)
            model = YOLO(self._w.text())
            imgs = [p for p in inp.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}]
            coco = {"images": [], "annotations": [], "categories": []}; ann_id = 1
            cls_counts = Counter(); self._rows = []
            for i, img in enumerate(imgs, 1):
                r = model.predict(str(img), conf=self._conf.value(), iou=self._iou.value(), verbose=False)[0]
                names = r.names
                boxes = r.boxes.xyxy.cpu().numpy() if r.boxes is not None else []
                cls = r.boxes.cls.int().cpu().tolist() if r.boxes is not None else []
                confs = r.boxes.conf.cpu().numpy().tolist() if r.boxes is not None else []
                kept = []
                for bi, b in enumerate(boxes):
                    if self._only.isChecked() and confs[bi] < self._conf.value():
                        continue
                    kept.append((b, cls[bi], confs[bi]))
                    cls_counts[names[cls[bi]]] += 1
                self._save_format(out, img, kept, names, coco, ann_id)
                ann_id += len(kept)
                self._rows.append([img.name, len(kept), ",".join(sorted({names[c] for _, c, _ in kept}))])
                self._prog.setValue(int(i / max(1, len(imgs)) * 100)); self._log.append(f"{img.name}: {len(kept)} objects")
            if self._fmt.currentText() == "COCO JSON":
                with open(out / "annotations.json", "w", encoding="utf-8") as f: json.dump(coco, f, ensure_ascii=False, indent=2)
            self._render()
            self._stats = {"total_images": len(imgs), "total_annotations": sum(cls_counts.values()), "per_class": dict(cls_counts)}
            self._st.setText(f"Статистика: {self._stats}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _save_format(self, out, img, kept, names, coco, ann_id):
        fmt = self._fmt.currentText()
        if fmt == "YOLO TXT":
            lines = []
            for (x1, y1, x2, y2), c, _ in kept:
                # fallback normalized by image size if available from cv2
                import cv2
                im = cv2.imread(str(img)); h, w = im.shape[:2]
                cx, cy = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
                bw, bh = (x2 - x1) / w, (y2 - y1) / h
                lines.append(f"{c} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            (out / f"{img.stem}.txt").write_text("\n".join(lines), encoding="utf-8")
        elif fmt == "Pascal VOC XML":
            root = ET.Element("annotation")
            ET.SubElement(root, "filename").text = img.name
            for (x1, y1, x2, y2), c, _ in kept:
                obj = ET.SubElement(root, "object"); ET.SubElement(obj, "name").text = names[c]
                bb = ET.SubElement(obj, "bndbox")
                for k, v in [("xmin", x1), ("ymin", y1), ("xmax", x2), ("ymax", y2)]: ET.SubElement(bb, k).text = str(int(v))
            ET.ElementTree(root).write(out / f"{img.stem}.xml", encoding="utf-8")
        else:
            coco["images"].append({"id": len(coco["images"]) + 1, "file_name": img.name})
            for (x1, y1, x2, y2), c, conf in kept:
                coco["annotations"].append({"id": ann_id, "image_id": len(coco["images"]), "category_id": int(c), "bbox": [float(x1), float(y1), float(x2 - x1), float(y2 - y1)], "score": float(conf)})
            if not coco["categories"]:
                coco["categories"] = [{"id": int(i), "name": n} for i, n in names.items()]

    def _render(self):
        self._table.setRowCount(len(self._rows))
        for i, r in enumerate(self._rows):
            for j, v in enumerate(r): self._table.setItem(i, j, QTableWidgetItem(str(v)))

    def _open_dir(self):
        if Path(self._out.text()).exists(): os.startfile(self._out.text())
