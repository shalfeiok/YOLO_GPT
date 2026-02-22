from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path

import yaml
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ExperimentsView(QWidget):
    def __init__(self, container) -> None:
        super().__init__()
        self._container = container
        self._rows: list[dict] = []
        self._build()
        self._scan()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self._flt = QLineEdit()
        self._flt.setPlaceholderText("Фильтр по названию")
        self._flt.textChanged.connect(self._apply)
        self._refresh = QPushButton("Обновить список")
        self._refresh.clicked.connect(self._scan)
        self._cmp = QPushButton("Сравнить выбранные")
        self._cmp.clicked.connect(self._compare)
        self._csv = QPushButton("Экспорт таблицы CSV")
        self._csv.clicked.connect(self._export)
        top.addWidget(self._flt, 1)
        top.addWidget(self._refresh)
        top.addWidget(self._cmp)
        top.addWidget(self._csv)
        root.addLayout(top)

        sp = QSplitter()
        root.addWidget(sp, 1)
        self._table = QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels(
            ["Запуск", "Дата", "Эпохи", "mAP50", "mAP50-95", "Final train loss", "Модель", "Датасет"]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self._table.itemSelectionChanged.connect(self._select)
        self._table.setSortingEnabled(True)
        sp.addWidget(self._table)

        right = QWidget()
        rl = QVBoxLayout(right)
        self._img = QLabel("results.png")
        self._img.setMinimumHeight(220)
        self._img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(self._img)
        self._args = QTreeWidget()
        self._args.setHeaderLabels(["Param", "Value"])
        rl.addWidget(self._args, 1)
        br = QHBoxLayout()
        self._open = QPushButton("Открыть папку")
        self._open.clicked.connect(self._open_dir)
        self._use = QPushButton("Использовать веса")
        self._use.clicked.connect(self._use_weights)
        br.addWidget(self._open)
        br.addWidget(self._use)
        rl.addLayout(br)
        sp.addWidget(right)
        sp.setStretchFactor(0, 3)
        sp.setStretchFactor(1, 2)

    def _read_results_metrics(self, results_csv: Path) -> tuple[int, float, float, float]:
        with results_csv.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        epochs = len(rows)
        if epochs == 0:
            return (0, 0.0, 0.0, 0.0)

        def _col_max(name: str) -> float:
            vals = [float(r.get(name, 0.0) or 0.0) for r in rows]
            return max(vals) if vals else 0.0

        def _col_last(name: str) -> float:
            return float(rows[-1].get(name, 0.0) or 0.0)

        return (
            epochs,
            _col_max("metrics/mAP50(B)"),
            _col_max("metrics/mAP50-95(B)"),
            _col_last("train/box_loss"),
        )

    def _scan(self) -> None:
        base = self._container.project_root / "runs" / "train"
        self._rows = []
        if not base.exists():
            self._render([])
            return

        for d in base.glob("*"):
            csvp = d / "results.csv"
            if not csvp.exists():
                continue
            try:
                epochs, map50, map95, loss = self._read_results_metrics(csvp)
                args_path = d / "args.yaml"
                args = (
                    yaml.safe_load(args_path.read_text(encoding="utf-8"))
                    if args_path.exists()
                    else {}
                )
                if not isinstance(args, dict):
                    args = {}
                self._rows.append(
                    {
                        "name": d.name,
                        "date_ts": d.stat().st_mtime,
                        "date": datetime.fromtimestamp(d.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "epochs": epochs,
                        "map50": map50,
                        "map": map95,
                        "loss": loss,
                        "model": str(args.get("model", "")),
                        "data": str(args.get("data", "")),
                        "dir": d,
                        "args": args,
                    }
                )
            except Exception:
                continue
        self._render(self._rows)

    def _render(self, rows: list[dict]) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [
                r["name"],
                r["date"],
                r["epochs"],
                r["map50"],
                r["map"],
                r["loss"],
                r["model"],
                r["data"],
            ]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(f"{v:.4f}" if isinstance(v, float) else str(v))
                self._table.setItem(i, j, it)
        self._table.setSortingEnabled(True)

    def _apply(self) -> None:
        q = self._flt.text().strip().lower()
        self._render([r for r in self._rows if q in r["name"].lower()])

    def _cur(self):
        row = self._table.currentRow()
        if row < 0:
            return None
        name_item = self._table.item(row, 0)
        if name_item is None:
            return None
        name = name_item.text()
        for x in self._rows:
            if x["name"] == name:
                return x
        return None

    def _select(self) -> None:
        x = self._cur()
        if not x:
            return
        rp = x["dir"] / "results.png"
        if rp.exists():
            self._img.setPixmap(QPixmap(str(rp)).scaledToHeight(220))
        self._args.clear()
        for k, v in x["args"].items():
            self._args.addTopLevelItem(QTreeWidgetItem([str(k), str(v)]))

    def _open_dir(self) -> None:
        x = self._cur()
        if x:
            os.startfile(str(x["dir"]))

    def _use_weights(self) -> None:
        x = self._cur()
        if not x:
            return
        p = x["dir"] / "weights" / "best.pt"
        if p.exists():
            QApplication.clipboard().setText(str(p))
            QMessageBox.information(self, "Готово", "Путь к весам скопирован в буфер")

    def _compare(self) -> None:
        sel = self._table.selectionModel().selectedRows()
        if len(sel) < 2:
            return
        rows = []
        for idx in sel:
            n = self._table.item(idx.row(), 0).text()
            found = next((r for r in self._rows if r["name"] == n), None)
            if found:
                rows.append(found)
        txt = "\n".join(
            [
                f"{r['name']}: mAP50={r['map50']:.4f}, mAP50-95={r['map']:.4f}, loss={r['loss']:.4f}"
                for r in rows
            ]
        )
        QMessageBox.information(self, "Сравнение", txt)

    def _export(self) -> None:
        p, _ = QFileDialog.getSaveFileName(self, "csv", "experiments.csv", "CSV (*.csv)")
        if not p:
            return
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["name", "date", "epochs", "map50", "map", "loss", "model", "data"])
            for r in self._rows:
                w.writerow([r["name"], r["date"], r["epochs"], r["map50"], r["map"], r["loss"], r["model"], r["data"]])
