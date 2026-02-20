"""Jobs view: history of background jobs with logs, retry, cancel.

This is a thin UI on top of JobRegistry + EventBus.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
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

from app.core.observability.crash_bundle import create_crash_bundle
from app.ui.infrastructure.file_dialogs import get_save_zip_path
from app.ui.views.jobs.policy_dialog import JobsPolicyDialog

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


class JobsView(QWidget):
    def __init__(self, container) -> None:
        super().__init__()
        self._container = container
        self._bus = container.event_bus
        self._registry = container.job_registry
        self._subs = []
        self._selected_job_id: str | None = None

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
        self._status_combo.addItems(["Все", "running", "retrying", "finished", "failed", "cancelled", "timed_out"])
        self._status_combo.currentIndexChanged.connect(self._refresh)
        header.addWidget(self._status_combo)

        self._clear_btn = QPushButton("Очистить")
        self._clear_btn.clicked.connect(self._on_clear)
        header.addWidget(self._clear_btn)

        self._bundle_btn = QPushButton("Crash bundle")
        self._bundle_btn.clicked.connect(self._on_crash_bundle)
        header.addWidget(self._bundle_btn)

        self._policy_btn = QPushButton("Политика")
        self._policy_btn.clicked.connect(self._on_policy)
        header.addWidget(self._policy_btn)

        root.addLayout(header)

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
        self._copy_summary_btn = QPushButton("Скопировать summary")
        self._copy_summary_btn.clicked.connect(self._on_copy_summary)
        self._bundle_btn2 = QPushButton("Crash bundle")
        self._bundle_btn2.clicked.connect(self._on_crash_bundle)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._retry_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self._copy_btn)
        btn_row.addWidget(self._copy_summary_btn)
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

    def _on_job_event(self, _e) -> None:
        # Job events can arrive from worker threads
        QTimer.singleShot(0, self._refresh)

    def _refresh(self) -> None:
        flt = self._filter_edit.text().strip().lower()
        status = self._status_combo.currentText()

        jobs = self._registry.list()
        if status != "Все":
            jobs = [j for j in jobs if j.status == status]
        if flt:
            jobs = [j for j in jobs if flt in j.name.lower() or flt in j.status.lower()]

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
            bar.setRange(0, 100)
            bar.setValue(int(j.progress * 100))
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

        self._refresh_details()

    @staticmethod
    def _format_status(status: str) -> str:
        return {
            "running": "🟢 running",
            "retrying": "🔁 retrying",
            "finished": "✅ finished",
            "failed": "❌ failed",
            "cancelled": "⛔ cancelled",
            "timed_out": "⏱ timed_out",
        }.get(status, status)

    def _on_select(self) -> None:
        items = self._table.selectedItems()
        if not items:
            self._selected_job_id = None
        else:
            self._selected_job_id = items[0].data(Qt.ItemDataRole.UserRole)
        self._refresh_details()

    def _refresh_details(self) -> None:
        rec = self._registry.get(self._selected_job_id) if self._selected_job_id else None
        if not rec:
            self._log.clear()
            self._cancel_btn.setEnabled(False)
            self._retry_btn.setEnabled(False)
            self._copy_btn.setEnabled(False)
            self._copy_summary_btn.setEnabled(False)
            return

        self._log.setPlainText("\n".join(rec.logs))
        if self._autoscroll.isChecked():
            self._log.moveCursor(self._log.textCursor().MoveOperation.End)

        self._cancel_btn.setEnabled(rec.status in {"running", "retrying"} and rec.cancel is not None)
        self._retry_btn.setEnabled(rec.rerun is not None and rec.status in {"failed", "cancelled", "finished", "timed_out"})
        self._copy_btn.setEnabled(True)
        self._copy_summary_btn.setEnabled(True)

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
            f"Job: {rec.name}",
            f"ID: {rec.job_id}",
            f"Status: {rec.status}",
            f"Progress: {int(rec.progress * 100)}%",
            f"Started: {rec.started_at.isoformat(timespec='seconds')}",
        ]
        if rec.ended_at:
            lines.append(f"Ended: {rec.ended_at.isoformat(timespec='seconds')}")
        if rec.message:
            lines.append(f"Message: {rec.message}")
        if rec.error:
            lines.append(f"Error: {rec.error}")
        # Include last ~25 log lines (enough context, still short)
        if rec.logs:
            lines.append("--- Tail log ---")
            lines.extend(rec.logs[-25:])
        QApplication.clipboard().setText("\n".join(lines))

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
        if dlg.exec():
            if getattr(self._container, "notifications", None):
                self._container.notifications.success("Политика задач сохранена")
