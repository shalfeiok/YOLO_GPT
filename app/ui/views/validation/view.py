from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.components.buttons import PrimaryButton, SecondaryButton


class ValidationView(QWidget):
    _job_event_signal = Signal(object)

    def __init__(self, container) -> None:
        super().__init__()
        self._container = container
        self._bus = container.event_bus
        self._job_runner = container.job_runner
        self._job_id: str | None = None
        self._last_result: dict[str, Any] | None = None
        self._result_dir: Path | None = None
        self._subs = []
        self._job_event_signal.connect(self._on_job_event_ui)
        self._build_ui()
        from app.core.events.job_events import JobFailed, JobFinished, JobLogLine

        self._subs.append(self._bus.subscribe_weak(JobLogLine, self._on_job_event))
        self._subs.append(self._bus.subscribe_weak(JobFinished, self._on_job_event))
        self._subs.append(self._bus.subscribe_weak(JobFailed, self._on_job_event))

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        cfg_group = QGroupBox("Параметры валидации")
        form = QFormLayout(cfg_group)

        self._weights = QLineEdit()
        btn_w = SecondaryButton("…")
        btn_w.clicked.connect(self._pick_weights)
        wr = QHBoxLayout(); wr.addWidget(self._weights, 1); wr.addWidget(btn_w)
        wc = QWidget(); wc.setLayout(wr)
        form.addRow("Веса (.pt):", wc)

        self._data = QLineEdit()
        btn_d = SecondaryButton("…")
        btn_d.clicked.connect(self._pick_data)
        dr = QHBoxLayout(); dr.addWidget(self._data, 1); dr.addWidget(btn_d)
        dc = QWidget(); dc.setLayout(dr)
        form.addRow("Dataset (data.yaml):", dc)

        self._device = QLineEdit("cpu")
        form.addRow("Устройство:", self._device)
        self._imgsz = QSpinBox(); self._imgsz.setRange(64, 4096); self._imgsz.setValue(640)
        form.addRow("Image size:", self._imgsz)
        self._conf = QDoubleSpinBox(); self._conf.setRange(0.0, 1.0); self._conf.setSingleStep(0.01); self._conf.setValue(0.25)
        form.addRow("Confidence:", self._conf)
        self._iou = QDoubleSpinBox(); self._iou.setRange(0.0, 1.0); self._iou.setSingleStep(0.01); self._iou.setValue(0.45)
        form.addRow("IOU:", self._iou)

        root.addWidget(cfg_group)

        btn_row = QHBoxLayout()
        self._run = PrimaryButton("Запустить валидацию")
        self._run.clicked.connect(self._start)
        self._export = SecondaryButton("Экспорт в JSON")
        self._export.clicked.connect(self._export_json)
        btn_row.addWidget(self._run)
        btn_row.addWidget(self._export)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Class", "Precision", "Recall", "mAP50", "mAP50-95"])
        root.addWidget(self._table, 1)

        self._result_path = QLabel("Результаты: -")
        root.addWidget(self._result_path)

        rbtn = QHBoxLayout()
        self._open_cm = QPushButton("Открыть confusion matrix")
        self._open_cm.clicked.connect(lambda: self._open_artifact("confusion_matrix.png"))
        self._open_pr = QPushButton("Открыть PR-кривую")
        self._open_pr.clicked.connect(lambda: self._open_artifact("PR_curve.png"))
        self._open_dir = QPushButton("Открыть папку результатов")
        self._open_dir.clicked.connect(self._open_dir_path)
        rbtn.addWidget(self._open_cm); rbtn.addWidget(self._open_pr); rbtn.addWidget(self._open_dir)
        root.addLayout(rbtn)

        self._log = QTextEdit(); self._log.setReadOnly(True)
        root.addWidget(self._log, 1)

    def _pick_weights(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Веса", "", "PyTorch (*.pt)")
        if p:
            self._weights.setText(p)

    def _pick_data(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "data.yaml", "", "YAML (*.yaml *.yml)")
        if p:
            self._data.setText(p)

    def _start(self) -> None:
        weights = Path(self._weights.text().strip())
        data = Path(self._data.text().strip())
        if not weights.exists() or not data.exists():
            QMessageBox.warning(self, "Ошибка", "Укажите существующие веса и data.yaml")
            return

        def _job(_token, progress):
            from ultralytics import YOLO

            progress(0.1, "loading model")
            model = YOLO(str(weights))
            progress(0.2, "running val")
            res = model.val(
                data=str(data),
                device=self._device.text().strip() or "cpu",
                imgsz=int(self._imgsz.value()),
                conf=float(self._conf.value()),
                iou=float(self._iou.value()),
            )
            progress(1.0, "done")
            names = getattr(res, "names", {}) or {}
            p = list(getattr(res.box, "p", [])) if hasattr(res, "box") else []
            r = list(getattr(res.box, "r", [])) if hasattr(res, "box") else []
            ap50 = list(getattr(res.box, "ap50", [])) if hasattr(res, "box") else []
            ap = list(getattr(res.box, "ap", [])) if hasattr(res, "box") else []
            rows = []
            for i in range(max(len(ap50), len(names))):
                rows.append({
                    "class": names.get(i, str(i)),
                    "precision": p[i] if i < len(p) else 0,
                    "recall": r[i] if i < len(r) else 0,
                    "map50": ap50[i] if i < len(ap50) else 0,
                    "map": ap[i] if i < len(ap) else 0,
                })
            save_dir = Path(getattr(res, "save_dir", ""))
            return {"rows": rows, "save_dir": str(save_dir)}

        handle = self._job_runner.submit("validation", _job)
        self._job_id = handle.job_id
        self._log.clear()
        self._run.setEnabled(False)

    def _on_job_event(self, event: object) -> None:
        self._job_event_signal.emit(event)

    def _on_job_event_ui(self, event: object) -> None:
        if getattr(event, "job_id", None) != self._job_id:
            return
        from app.core.events.job_events import JobFailed, JobFinished, JobLogLine

        if isinstance(event, JobLogLine):
            self._log.append(event.line)
        elif isinstance(event, JobFailed):
            self._run.setEnabled(True)
            QMessageBox.critical(self, "Validation error", event.error)
        elif isinstance(event, JobFinished):
            self._run.setEnabled(True)
            self._last_result = event.result
            self._fill_table(event.result.get("rows", []))
            self._result_dir = Path(event.result.get("save_dir", ""))
            self._result_path.setText(f"Результаты: {self._result_dir}")

    def _fill_table(self, rows: list[dict[str, Any]]) -> None:
        self._table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            vals = [row["class"], row["precision"], row["recall"], row["map50"], row["map"]]
            for c, v in enumerate(vals):
                text = f"{v:.4f}" if isinstance(v, float) else str(v)
                self._table.setItem(i, c, QTableWidgetItem(text))

    def _open_artifact(self, name: str) -> None:
        if not self._result_dir:
            return
        p = self._result_dir / name
        if p.exists():
            os.startfile(str(p))

    def _open_dir_path(self) -> None:
        if self._result_dir and self._result_dir.exists():
            os.startfile(str(self._result_dir))

    def _export_json(self) -> None:
        if not self._last_result:
            return
        p, _ = QFileDialog.getSaveFileName(self, "JSON", "validation_metrics.json", "JSON (*.json)")
        if not p:
            return
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self._last_result, f, ensure_ascii=False, indent=2)

    def closeEvent(self, event) -> None:  # noqa: N802
        for s in self._subs:
            self._bus.unsubscribe(s)
        super().closeEvent(event)
