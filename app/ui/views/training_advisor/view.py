from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.application.use_cases.training_advisor import AnalyzeTrainingRequest
from app.domain.training_config import TrainingConfig, export_training_config


class _AnalyzerWorker(QThread):
    done = Signal(object, object)

    def __init__(self, parent: QWidget, request: AnalyzeTrainingRequest, use_case) -> None:
        super().__init__(parent)
        self._request = request
        self._use_case = use_case

    def run(self) -> None:
        try:
            report = self._use_case.execute(self._request)
            self.done.emit(report, None)
        except Exception as e:
            self.done.emit(None, str(e))


class TrainingAdvisorView(QWidget):
    def __init__(self, container) -> None:
        super().__init__()
        self._container = container
        self._report = None
        self._worker = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        form_box = QGroupBox("Советник по обучению")
        form = QFormLayout(form_box)
        self._weights = QLineEdit()
        self._dataset = QLineEdit()
        self._run = QLineEdit()
        form.addRow("Путь к весам модели (.pt):", self._path_row(self._weights, True))
        form.addRow("Путь к датасету (data.yaml или папка):", self._path_row(self._dataset, False))
        form.addRow("Папка прошлого запуска (опционально):", self._path_row(self._run, False, folder_only=True))
        mode_row = QHBoxLayout()
        self._quick = QRadioButton("Быстрый анализ")
        self._deep = QRadioButton("Глубокий анализ")
        self._quick.setChecked(True)
        mode_row.addWidget(self._quick)
        mode_row.addWidget(self._deep)
        form.addRow("Режим:", self._widget_from_layout(mode_row))
        self._analyze_btn = QPushButton("Проанализировать")
        self._analyze_btn.clicked.connect(self._analyze)
        form.addRow("", self._analyze_btn)
        root.addWidget(form_box)

        self._result = QTextEdit()
        self._result.setReadOnly(True)
        root.addWidget(self._result, 1)

        actions = QHBoxLayout()
        self._export_btn = QPushButton("Экспорт рекомендаций")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export)
        self._send_btn = QPushButton("Передать в обучение")
        self._send_btn.setEnabled(False)
        self._send_btn.clicked.connect(self._send_to_training)
        actions.addWidget(self._export_btn)
        actions.addWidget(self._send_btn)
        root.addLayout(actions)

    def _widget_from_layout(self, layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    def _path_row(self, edit: QLineEdit, required: bool, folder_only: bool = False) -> QWidget:
        row = QHBoxLayout()
        row.addWidget(edit, 1)
        btn = QPushButton("…")

        def _pick() -> None:
            if folder_only:
                path = QFileDialog.getExistingDirectory(self, "Выберите папку")
            elif edit is self._weights:
                path, _ = QFileDialog.getOpenFileName(self, "Выберите веса", filter="PyTorch (*.pt)")
            else:
                path = QFileDialog.getExistingDirectory(self, "Выберите папку датасета")
            if path:
                edit.setText(path)

        btn.clicked.connect(_pick)
        row.addWidget(btn)
        if required:
            req = QLabel("*")
            row.addWidget(req)
        return self._widget_from_layout(row)

    def _analyze(self) -> None:
        if not self._weights.text().strip() or not self._dataset.text().strip():
            QMessageBox.warning(self, "Советник по обучению", "Укажите пути к весам и датасету")
            return
        current_cfg = TrainingConfig.from_current_state(self._container.last_training_state or {})
        request = AnalyzeTrainingRequest(
            model_weights_path=Path(self._weights.text().strip()),
            dataset_path=Path(self._dataset.text().strip()),
            run_folder_path=Path(self._run.text().strip()) if self._run.text().strip() else None,
            mode="Deep" if self._deep.isChecked() else "Quick",
            current_training_config=current_cfg,
        )
        self._analyze_btn.setEnabled(False)
        self._result.setPlainText("Выполняется анализ...")
        self._worker = _AnalyzerWorker(self, request, self._container.analyze_training_advisor_use_case)
        self._worker.done.connect(self._on_report)
        self._worker.start()

    def _on_report(self, report, error) -> None:
        self._analyze_btn.setEnabled(True)
        if error:
            self._result.setPlainText(f"Ошибка: {error}")
            return
        self._report = report
        lines = ["# Состояние датасета", str(report.dataset_health), "", "# Сводка запуска", str(report.run_summary), "", "# Оценка модели", str(report.model_eval), "", "# Рекомендации"]
        for item in report.recommendations:
            lines.append(f"- {item.param}: {item.current} -> {item.recommended} ({item.reason}, conf={item.confidence:.2f})")
        if report.diff:
            lines.append("\n# Изменения")
            for d in report.diff:
                lines.append(f"- {d['param']}: {d['current']} -> {d['recommended']}")
        self._result.setPlainText("\n".join(lines))
        self._export_btn.setEnabled(True)
        self._send_btn.setEnabled(True)

    def _export(self) -> None:
        if not self._report:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт конфигурации", "advisor_recommended.yaml", "YAML (*.yaml);;JSON (*.json)")
        if not path:
            return
        export_training_config(Path(path), self._report.recommended_training_config)

    def _send_to_training(self) -> None:
        if not self._report:
            return
        self._container.advisor_store.update(
            report=self._report,
            model_weights=self._weights.text().strip(),
            dataset=self._dataset.text().strip(),
            run_folder=self._run.text().strip() or None,
        )
        QMessageBox.information(self, "Советник по обучению", "Рекомендации переданы во вкладку «Обучение»")
