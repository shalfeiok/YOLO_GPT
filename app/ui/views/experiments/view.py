from __future__ import annotations

import csv
import os
from pathlib import Path

import pandas as pd
import yaml
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class ExperimentsView(QWidget):
    def __init__(self, container) -> None:
        super().__init__(); self._container = container; self._rows = []; self._build(); self._scan()

    def _build(self):
        root = QVBoxLayout(self)
        top = QHBoxLayout(); self._flt = QLineEdit(); self._flt.setPlaceholderText("Фильтр по названию"); self._flt.textChanged.connect(self._apply)
        self._refresh = QPushButton("Обновить список"); self._refresh.clicked.connect(self._scan)
        self._cmp = QPushButton("Сравнить выбранные"); self._cmp.clicked.connect(self._compare)
        self._csv = QPushButton("Экспорт таблицы CSV"); self._csv.clicked.connect(self._export)
        top.addWidget(self._flt, 1); top.addWidget(self._refresh); top.addWidget(self._cmp); top.addWidget(self._csv); root.addLayout(top)
        sp = QSplitter(); root.addWidget(sp, 1)
        self._table = QTableWidget(0, 8); self._table.setHorizontalHeaderLabels(["Запуск", "Дата", "Эпохи", "mAP50", "mAP50-95", "Final train loss", "Модель", "Датасет"])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self._table.itemSelectionChanged.connect(self._select)
        sp.addWidget(self._table)
        right = QWidget(); rl = QVBoxLayout(right)
        self._img = QLabel("results.png"); self._img.setMinimumHeight(220); self._img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(self._img)
        self._args = QTreeWidget(); self._args.setHeaderLabels(["Param", "Value"]); rl.addWidget(self._args, 1)
        br = QHBoxLayout(); self._open = QPushButton("Открыть папку"); self._open.clicked.connect(self._open_dir)
        self._use = QPushButton("Использовать веса"); self._use.clicked.connect(self._use_weights)
        br.addWidget(self._open); br.addWidget(self._use); rl.addLayout(br)
        sp.addWidget(right); sp.setStretchFactor(0, 3); sp.setStretchFactor(1, 2)

    def _scan(self):
        base = self._container.project_root / "runs" / "train"
        self._rows = []
        for d in base.glob("*"):
            csvp = d / "results.csv"
            if not csvp.exists():
                continue
            try:
                df = pd.read_csv(csvp)
                args = yaml.safe_load((d / "args.yaml").read_text(encoding="utf-8")) if (d / "args.yaml").exists() else {}
                self._rows.append({
                    "name": d.name,
                    "date": d.stat().st_mtime,
                    "epochs": len(df),
                    "map50": float(df.get("metrics/mAP50(B)", pd.Series([0])).max()),
                    "map": float(df.get("metrics/mAP50-95(B)", pd.Series([0])).max()),
                    "loss": float(df.get("train/box_loss", pd.Series([0])).iloc[-1]),
                    "model": args.get("model", ""),
                    "data": args.get("data", ""),
                    "dir": d,
                    "args": args,
                })
            except Exception:
                continue
        self._render(self._rows)

    def _render(self, rows):
        self._table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [r["name"], str(r["date"]), r["epochs"], r["map50"], r["map"], r["loss"], r["model"], r["data"]]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(f"{v:.4f}" if isinstance(v, float) else str(v)); self._table.setItem(i, j, it)

    def _apply(self):
        q = self._flt.text().strip().lower()
        self._render([r for r in self._rows if q in r["name"].lower()])

    def _cur(self):
        r = self._table.currentRow()
        if r < 0: return None
        name = self._table.item(r, 0).text()
        for x in self._rows:
            if x["name"] == name: return x
        return None

    def _select(self):
        x = self._cur()
        if not x: return
        rp = x["dir"] / "results.png"
        if rp.exists(): self._img.setPixmap(QPixmap(str(rp)).scaledToHeight(220))
        self._args.clear()
        for k, v in x["args"].items(): self._args.addTopLevelItem(QTreeWidgetItem([str(k), str(v)]))

    def _open_dir(self):
        x = self._cur()
        if x: os.startfile(str(x["dir"]))

    def _use_weights(self):
        x = self._cur()
        if not x: return
        p = x["dir"] / "weights" / "best.pt"
        if p.exists():
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(str(p))
            QMessageBox.information(self, "Готово", "Путь к весам скопирован в буфер")

    def _compare(self):
        sel = self._table.selectionModel().selectedRows()
        if len(sel) < 2: return
        rows = []
        for idx in sel:
            n = self._table.item(idx.row(), 0).text()
            rows.append(next(r for r in self._rows if r["name"] == n))
        txt = "\n".join([f"{r['name']}: mAP50={r['map50']:.4f}, mAP50-95={r['map']:.4f}, loss={r['loss']:.4f}" for r in rows])
        QMessageBox.information(self, "Сравнение", txt)

    def _export(self):
        p, _ = QFileDialog.getSaveFileName(self, "csv", "experiments.csv", "CSV (*.csv)")
        if not p: return
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["name", "date", "epochs", "map50", "map", "loss", "model", "data"])
            for r in self._rows: w.writerow([r["name"], r["date"], r["epochs"], r["map50"], r["map"], r["loss"], r["model"], r["data"]])
