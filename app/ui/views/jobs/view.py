"""Jobs view: history of background jobs with logs, retry, cancel.

This is a thin UI on top of JobRegistry + EventBus.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.events.job_events import (
    JobCancelled,
    JobFailed,
    JobFinished,
    JobLogLine,
    JobProgress,
    JobRetrying,
    JobStarted,
    JobTimedOut,
)
from app.core.observability.crash_bundle import create_crash_bundle
from app.core.observability.run_manifest import get_run_folder
from app.ui.infrastructure.file_dialogs import get_save_zip_path
from app.ui.views.jobs.policy_dialog import JobsPolicyDialog


class JobsView(QWidget):
    def __init__(self, container) -> None:
        super().__init__()
        self._container = container
        self._bus = container.event_bus
        self._registry = container.job_registry
        self._subs = []
        self._selected_job_id: str | None = None
        self._refresh_scheduled = False
        self._details_job_id: str | None = None
        self._details_log_count = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(QLabel("Задачи"))
        header.addStretch(1)

        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Фильтр по имени/статусу…")
        self._filter_edit.textChanged.connect(self._refresh)
        header.addWidget(self._filter_edit, 2)

        self._status_combo = QComboBox()
        self._status_combo.addItems(
            ["Все", "running", "retrying", "finished", "failed", "cancelled", "timed_out"]
        )
        self._status_combo.currentIndexChanged.connect(self._refresh)
        header.addWidget(self._status_combo)

        self._clear_btn = QPushButton("Очистить")
        self._clear_btn.clicked.connect(self._on_clear)
        header.addWidget(self._clear_btn)

        self._bundle_btn = QPushButton("Крэш-архив")
        self._bundle_btn.clicked.connect(self._on_crash_bundle)
        header.addWidget(self._bundle_btn)

        self._policy_btn = QPushButton("Политика")
        self._policy_btn.clicked.connect(self._on_policy)
        header.addWidget(self._policy_btn)

        root.addLayout(header)

        # Empty-state label (shown when there are no jobs)
        self._empty_label = QLabel("Нет задач")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        root.addWidget(self._empty_label)

        splitter = QSplitter(Qt.Orientation.Vertical)
        root.addWidget(splitter, 1)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Время", "Имя", "Статус", "Прогресс", "Сообщение"])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.itemSelectionChanged.connect(self._on_select)
        self._table.horizontalHeader().setStretchLastSection(True)
        splitter.addWidget(self._table)

        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(6)

        btn_row = QHBoxLayout()
        self._cancel_btn = QPushButton("Отменить")
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._retry_btn = QPushButton("Повторить")
        self._retry_btn.clicked.connect(self._on_retry)
        self._copy_btn = QPushButton("Скопировать лог")
        self._copy_btn.clicked.connect(self._on_copy_log)
        self._copy_summary_btn = QPushButton("Скопировать сводку")
        self._copy_summary_btn.clicked.connect(self._on_copy_summary)
        self._open_run_btn = QPushButton("Открыть папку запуска")
        self._open_run_btn.clicked.connect(self._on_open_run_folder)
        self._open_manifest_btn = QPushButton("Манифест")
        self._open_manifest_btn.clicked.connect(self._on_open_manifest)
        self._open_weights_btn = QPushButton("Веса")
        self._open_weights_btn.clicked.connect(self._on_open_weights)
        self._open_plots_btn = QPushButton("Графики")
        self._open_plots_btn.clicked.connect(self._on_open_plots)
        self._bundle_btn2 = QPushButton("Крэш-архив")
        self._bundle_btn2.clicked.connect(self._on_crash_bundle)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._retry_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self._copy_btn)
        btn_row.addWidget(self._copy_summary_btn)
        btn_row.addWidget(self._open_run_btn)
        btn_row.addWidget(self._open_manifest_btn)
        btn_row.addWidget(self._open_weights_btn)
        btn_row.addWidget(self._open_plots_btn)
        btn_row.addWidget(self._bundle_btn2)
        bottom_layout.addLayout(btn_row)

        log_controls = QHBoxLayout()
        self._log_search = QLineEdit()
        self._log_search.setPlaceholderText("Поиск по логу…")
        self._log_search.returnPressed.connect(self._on_find_next)
        self._find_prev_btn = QPushButton("Назад")
        self._find_prev_btn.clicked.connect(self._on_find_prev)
        self._find_next_btn = QPushButton("Вперёд")
        self._find_next_btn.clicked.connect(self._on_find_next)
        self._autoscroll = QCheckBox("Автоскролл")
        self._autoscroll.setChecked(True)
        log_controls.addWidget(self._log_search, 2)
        log_controls.addWidget(self._find_prev_btn)
        log_controls.addWidget(self._find_next_btn)
        log_controls.addStretch(1)
        log_controls.addWidget(self._autoscroll)
        bottom_layout.addLayout(log_controls)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("Выберите задачу, чтобы увидеть лог…")
        bottom_layout.addWidget(self._log, 1)
        splitter.addWidget(bottom)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        # Subscribe to job events (thread-safe UI updates)
        self._subs.append(self._bus.subscribe_weak(JobStarted, self._on_job_event))
        self._subs.append(self._bus.subscribe_weak(JobProgress, self._on_job_event))
        self._subs.append(self._bus.subscribe_weak(JobLogLine, self._on_job_event))
        self._subs.append(self._bus.subscribe_weak(JobFinished, self._on_job_event))
        self._subs.append(self._bus.subscribe_weak(JobFailed, self._on_job_event))
        self._subs.append(self._bus.subscribe_weak(JobCancelled, self._on_job_event))
        self._subs.append(self._bus.subscribe_weak(JobRetrying, self._on_job_event))
        self._subs.append(self._bus.subscribe_weak(JobTimedOut, self._on_job_event))

        self._refresh()

    def closeEvent(self, event) -> None:  # noqa: N802
        for s in self._subs:
            self._bus.unsubscribe(s)
        self._subs.clear()
        super().closeEvent(event)

    def _on_job_event(self, event) -> None:
        # Job events can arrive from worker threads.
        QTimer.singleShot(0, lambda e=event: self._on_job_event_ui(e))

    def _on_job_event_ui(self, event) -> None:
        if isinstance(event, JobLogLine) and event.job_id == self._selected_job_id:
            self._append_log_lines(event.line.splitlines())
        if self._refresh_scheduled:
            return
        self._refresh_scheduled = True
        QTimer.singleShot(120, self._refresh_debounced)

    def _refresh_debounced(self) -> None:
        self._refresh_scheduled = False
        self._refresh()

    def _refresh(self) -> None:
        flt = self._filter_edit.text().strip().lower()
        status = self._status_combo.currentText()

        jobs = self._registry.list()
        if status != "Все":
            jobs = [j for j in jobs if j.status == status]
        if flt:
            jobs = [j for j in jobs if flt in j.name.lower() or flt in j.status.lower()]

        self._table.setUpdatesEnabled(False)
        self._table.setRowCount(len(jobs))

        has_jobs = len(jobs) > 0
        self._table.setVisible(has_jobs)
        self._empty_label.setVisible(not has_jobs)
        for r, j in enumerate(jobs):
            t = j.started_at.strftime("%H:%M:%S")
            self._table.setItem(r, 0, QTableWidgetItem(t))
            self._table.setItem(r, 1, QTableWidgetItem(j.name))
            self._table.setItem(r, 2, QTableWidgetItem(self._format_status(j.status)))

            # Progress as a real progress bar (better UX than plain text)
            bar = QProgressBar()
            if j.status in {"running", "retrying"} and j.progress <= 0.0:
                bar.setRange(0, 0)
                bar.setFormat("Выполняется…")
            else:
                bar.setRange(0, 100)
                bar.setValue(int(j.progress * 100))
                bar.setFormat(f"{int(j.progress * 100)}%")
            bar.setTextVisible(True)
            self._table.setCellWidget(r, 3, bar)
            self._table.setItem(r, 4, QTableWidgetItem(j.message or j.error or ""))
            # Store job_id on first column
            self._table.item(r, 0).setData(Qt.ItemDataRole.UserRole, j.job_id)

        # Keep selection if possible
        if self._selected_job_id:
            for r in range(self._table.rowCount()):
                it = self._table.item(r, 0)
                if it and it.data(Qt.ItemDataRole.UserRole) == self._selected_job_id:
                    self._table.selectRow(r)
                    break

        self._table.setUpdatesEnabled(True)

        self._refresh_details()

    @staticmethod
    def _format_status(status: str) -> str:
        return {
            "running": "🟢 выполняется",
            "retrying": "🔁 повтор",
            "finished": "✅ завершена",
            "failed": "❌ ошибка",
            "cancelled": "⛔ отменена",
            "timed_out": "⏱ таймаут",
        }.get(status, status)

    def _on_select(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            self._selected_job_id = None
        else:
            item = self._table.item(row, 0)
            self._selected_job_id = None if item is None else item.data(Qt.ItemDataRole.UserRole)
        self._refresh_details()

    def _refresh_details(self) -> None:
        rec = self._registry.get(self._selected_job_id) if self._selected_job_id else None
        if not rec:
            self._log.clear()
            self._details_job_id = None
            self._details_log_count = 0
            self._cancel_btn.setEnabled(False)
            self._retry_btn.setEnabled(False)
            self._copy_btn.setEnabled(False)
            self._copy_summary_btn.setEnabled(False)
            self._open_run_btn.setEnabled(False)
            self._open_manifest_btn.setEnabled(False)
            self._open_weights_btn.setEnabled(False)
            self._open_plots_btn.setEnabled(False)
            return

        if self._details_job_id != rec.job_id or len(rec.logs) < self._details_log_count:
            self._log.setPlainText("\n".join(rec.logs))
        elif len(rec.logs) > self._details_log_count:
            self._append_log_lines(rec.logs[self._details_log_count :])
        self._details_job_id = rec.job_id
        self._details_log_count = len(rec.logs)

        self._cancel_btn.setEnabled(
            rec.status in {"running", "retrying"} and rec.cancel is not None
        )
        self._retry_btn.setEnabled(
            rec.rerun is not None and rec.status in {"failed", "cancelled", "finished", "timed_out"}
        )
        self._copy_btn.setEnabled(True)
        self._copy_summary_btn.setEnabled(True)
        folder = get_run_folder(rec.job_id)
        self._open_run_btn.setEnabled(folder is not None)
        self._open_manifest_btn.setEnabled(
            folder is not None and (folder / "run_manifest.json").exists()
        )
        self._open_weights_btn.setEnabled(folder is not None and any(folder.rglob("best.pt")))
        self._open_plots_btn.setEnabled(folder is not None and any(folder.rglob("results.png")))

    def _on_cancel(self) -> None:
        rec = self._registry.get(self._selected_job_id) if self._selected_job_id else None
        if rec and rec.cancel:
            rec.cancel()

    def _on_retry(self) -> None:
        rec = self._registry.get(self._selected_job_id) if self._selected_job_id else None
        if rec and rec.rerun:
            rec.rerun()

    def _on_copy_log(self) -> None:
        rec = self._registry.get(self._selected_job_id) if self._selected_job_id else None
        if not rec:
            return
        cb = QApplication.clipboard()
        cb.setText("\n".join(rec.logs))

    def _on_copy_summary(self) -> None:
        rec = self._registry.get(self._selected_job_id) if self._selected_job_id else None
        if not rec:
            return
        lines = [
            f"Задача: {rec.name}",
            f"ID: {rec.job_id}",
            f"Статус: {rec.status}",
            f"Прогресс: {int(rec.progress * 100)}%",
            f"Старт: {rec.started_at.isoformat(timespec='seconds')}",
        ]
        if rec.finished_at:
            lines.append(f"Завершено: {rec.finished_at.isoformat(timespec='seconds')}")
        if rec.message:
            lines.append(f"Сообщение: {rec.message}")
        if rec.error:
            lines.append(f"Ошибка: {rec.error}")
        # Include last ~25 log lines (enough context, still short)
        if rec.logs:
            lines.append("--- Хвост лога ---")
            lines.extend(rec.logs[-25:])
        QApplication.clipboard().setText("\n".join(lines))

    def _append_log_lines(self, lines: list[str]) -> None:
        if not lines:
            return
        self._log.moveCursor(self._log.textCursor().MoveOperation.End)
        if self._log.toPlainText():
            self._log.insertPlainText("\n")
        self._log.insertPlainText("\n".join(lines))
        if self._autoscroll.isChecked():
            self._log.moveCursor(self._log.textCursor().MoveOperation.End)

    def _on_find_next(self) -> None:
        needle = self._log_search.text().strip()
        if not needle:
            return
        doc = self._log.document()
        cur = self._log.textCursor()
        found = doc.find(needle, cur)
        if found.isNull():
            found = doc.find(needle)  # wrap
        if not found.isNull():
            self._log.setTextCursor(found)

    def _on_find_prev(self) -> None:
        needle = self._log_search.text().strip()
        if not needle:
            return
        doc = self._log.document()
        cur = self._log.textCursor()
        found = doc.find(needle, cur, QTextEdit.FindFlag.FindBackward)
        if found.isNull():
            end = self._log.textCursor()
            end.movePosition(end.MoveOperation.End)
            found = doc.find(needle, end, QTextEdit.FindFlag.FindBackward)
        if not found.isNull():
            self._log.setTextCursor(found)

    def _open_path(self, path) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _selected_run_folder(self):
        rec = self._registry.get(self._selected_job_id) if self._selected_job_id else None
        if rec is None:
            return None
        return get_run_folder(rec.job_id)

    def _on_open_manifest(self) -> None:
        folder = self._selected_run_folder()
        if folder is None:
            return
        manifest = folder / "run_manifest.json"
        if manifest.exists():
            self._open_path(manifest)

    def _on_open_weights(self) -> None:
        folder = self._selected_run_folder()
        if folder is None:
            return
        weights = next(folder.rglob("best.pt"), None)
        if weights is not None:
            self._open_path(weights.parent)

    def _on_open_plots(self) -> None:
        folder = self._selected_run_folder()
        if folder is None:
            return
        plot = next(folder.rglob("results.png"), None)
        if plot is not None:
            self._open_path(plot)

    def _on_open_run_folder(self) -> None:
        rec = self._registry.get(self._selected_job_id) if self._selected_job_id else None
        if rec is None:
            return
        folder = get_run_folder(rec.job_id)
        if folder is None:
            if getattr(self._container, "notifications", None):
                self._container.notifications.warning("Для этой задачи не найден run folder")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _on_clear(self) -> None:
        self._registry.clear()
        self._selected_job_id = None
        self._refresh()

    def _on_crash_bundle(self) -> None:
        out = get_save_zip_path(self, title="Сохранить crash bundle")
        if out is None:
            return
        try:
            create_crash_bundle(out)
            if getattr(self._container, "notifications", None):
                self._container.notifications.success(f"Crash bundle сохранён: {out}")
        except Exception as e:
            if getattr(self._container, "notifications", None):
                self._container.notifications.error(f"Не удалось создать crash bundle: {e}")

    def _on_policy(self) -> None:
        dlg = JobsPolicyDialog(self, integrations=getattr(self._container, "integrations", None))
        if dlg.exec() and getattr(self._container, "notifications", None):
            self._container.notifications.success("Политика задач сохранена")
