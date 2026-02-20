"""Integrations view.

The UI is split into section builders in :mod:`app.ui.views.integrations.sections` to keep this
module readable.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QTextEdit,
)
from PySide6.QtCore import QTimer

from app.config import INTEGRATIONS_CONFIG_PATH

from app.ui.views.integrations.sections import (
    SectionsCtx,
    build_comet,
    build_dvc,
    build_export,
    build_kfold,
    build_sagemaker,
    build_sahi,
    build_seg_isolation,
    build_tuning,
    build_validation,
)

from app.ui.views.integrations.view_model import IntegrationsViewModel
from app.core.events import (
    JobCancelled,
    JobFailed,
    JobFinished,
    JobLogLine,
    JobProgress,
    JobRetrying,
    JobStarted,
    JobTimedOut,
)

from app.ui.infrastructure.file_dialogs import (
    get_open_json_path,
    get_save_json_path,
)

from app.ui.components.buttons import PrimaryButton, SecondaryButton
from app.ui.components.inputs import NoWheelSpinBox
from app.ui.theme.tokens import Tokens

if TYPE_CHECKING:
    from app.ui.infrastructure.di import Container

LABEL_WIDTH = 200


class IntegrationsView(QWidget):
    """Вкладка «Интеграции»: экспорт/импорт конфигурации, ссылки на документацию."""

    def __init__(self, container: 'Container | None' = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._vm = IntegrationsViewModel(container)
        self._state = self._vm.load_state()
        self._current_job_id: str | None = None
        self._subs = []
        self._root_layout = QVBoxLayout(self)
        # Auto-refresh after imports/resets from the ViewModel.
        try:
            self._vm.state_changed.connect(self._on_state_changed)  # type: ignore[attr-defined]
        except Exception:
            import logging
            logging.getLogger(__name__).debug('Integrations view update failed', exc_info=True)
        # Subscribe to background job events (published from worker threads).
        if self._container:
            bus = self._container.event_bus
            # Use weak subscriptions to avoid leaks when the view is destroyed.
            self._subs.append(bus.subscribe_weak(JobStarted, self._on_job_event))
            self._subs.append(bus.subscribe_weak(JobProgress, self._on_job_event))
            self._subs.append(bus.subscribe_weak(JobFinished, self._on_job_event))
            self._subs.append(bus.subscribe_weak(JobFailed, self._on_job_event))
            self._subs.append(bus.subscribe_weak(JobCancelled, self._on_job_event))
            self._subs.append(bus.subscribe_weak(JobRetrying, self._on_job_event))
            self._subs.append(bus.subscribe_weak(JobTimedOut, self._on_job_event))
            self._subs.append(bus.subscribe_weak(JobLogLine, self._on_job_event))
        self._build_ui()

    def closeEvent(self, event) -> None:  # noqa: N802
        # Explicitly detach handlers (also safe with weak subscriptions).
        if self._container:
            bus = self._container.event_bus
            for s in self._subs:
                bus.unsubscribe(s)
        self._subs.clear()
        super().closeEvent(event)

    def _on_job_event(self, event: object) -> None:
        # Marshal to Qt main thread.
        QTimer.singleShot(0, lambda e=event: self._handle_job_event(e))

    def _handle_job_event(self, event: object) -> None:
        if not hasattr(self, "_job_status"):
            return
        # Only show status for the currently tracked job.
        job_id = getattr(event, "job_id", None)
        if self._current_job_id and job_id != self._current_job_id:
            return

        if isinstance(event, JobStarted):
            self._current_job_id = event.job_id
            self._job_status.setText(f"Задача: {event.name} — запуск…")
            self._btn_cancel_job.setEnabled(True)
            if hasattr(self, "_job_log"):
                self._job_log.setPlainText("")
        elif isinstance(event, JobProgress):
            pct = int(event.progress * 100)
            msg = f" — {event.message}" if event.message else ""
            self._job_status.setText(f"Задача: {event.name} — {pct}%{msg}")
        elif isinstance(event, JobRetrying):
            self._job_status.setText(
                f"Задача: {event.name} — повтор {event.attempt}/{event.max_attempts}: {event.error}"
            )
        elif isinstance(event, JobFinished):
            self._job_status.setText(f"Задача: {event.name} — готово")
            self._btn_cancel_job.setEnabled(False)
            self._current_job_id = None
            # Show a friendly completion toast with key results.
            try:
                if event.name == "export_model" and event.result:
                    self._toast_ok("Экспорт", f"Готово: {event.result}")
                elif event.name == "validate_model" and isinstance(event.result, dict):
                    metrics = event.result
                    msg = "Готово.\n" + "\n".join(
                        f"{k}: {float(v):.4f}" for k, v in metrics.items() if v is not None
                    )
                    self._toast_ok("Валидация", msg)
                elif event.name == "seg_isolate" and event.result is not None:
                    self._toast_ok("Seg isolation", f"Сохранено изображений: {event.result}.")
                elif event.name == "kfold_split" and isinstance(event.result, list):
                    self._toast_ok("K-Fold", f"Разбиение выполнено. YAML файлов: {len(event.result)}")
                elif event.name == "kfold_train" and isinstance(event.result, list):
                    self._toast_ok("K-Fold", f"Обучение завершено. Весов: {len(event.result)}")
                elif event.name == "tune" and event.result:
                    self._toast_ok("Tuning", f"Готово: {event.result}")
                elif event.name == "sahi_predict":
                    self._toast_ok("SAHI", "Инференс по плиткам завершён.")
                elif event.name in {"sagemaker_clone_template", "sagemaker_cdk_deploy"} and isinstance(event.result, tuple):
                    ok, msg = event.result
                    (self._toast_ok if ok else self._toast_warn)("SageMaker", msg)
            except Exception:
                import logging
                logging.getLogger(__name__).debug('Integrations view update failed', exc_info=True)
        elif isinstance(event, JobFailed):
            self._job_status.setText(f"Задача: {event.name} — ошибка")
            self._btn_cancel_job.setEnabled(False)
            self._current_job_id = None
            self._toast_err("Ошибка задачи", event.error)
        elif isinstance(event, JobCancelled):
            self._job_status.setText(f"Задача: {event.name} — отменено")
            self._btn_cancel_job.setEnabled(False)
            self._current_job_id = None
            self._toast_warn("Отмена", "Задача отменена.")
        elif isinstance(event, JobTimedOut):
            self._job_status.setText(f"Задача: {event.name} — таймаут")
            self._btn_cancel_job.setEnabled(False)
            self._current_job_id = None
            self._toast_err("Таймаут", f"Превышено время: {event.timeout_sec:.1f}с")
        elif isinstance(event, JobLogLine):
            if hasattr(self, "_job_log"):
                self._append_job_log(event.line)

    def _append_job_log(self, line: str) -> None:
        # Keep the log bounded.
        txt = self._job_log.toPlainText()
        lines = (txt.splitlines() + [line])[-400:]
        self._job_log.setPlainText("\n".join(lines))
        self._job_log.verticalScrollBar().setValue(self._job_log.verticalScrollBar().maximum())

    def _on_state_changed(self, state: object) -> None:
        self._state = state  # type: ignore[assignment]
        self._rebuild_ui()

    def _rebuild_ui(self) -> None:
        """Rebuild the view from the current state.

        This keeps the implementation simple and guarantees the UI reflects the persisted
        config after an import.
        """

        layout = self._root_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
            else:
                # nested layouts
                l = item.layout()
                if l is not None:
                    while l.count():
                        i2 = l.takeAt(0)
                        w2 = i2.widget()
                        if w2 is not None:
                            w2.setParent(None)
        self._build_ui()

    def _toast_ok(self, title: str, message: str) -> None:
        if self._container and self._container.notifications:
            self._container.notifications.success(title, message)
            return
        QMessageBox.information(self, title, message)

    def _toast_warn(self, title: str, message: str) -> None:
        if self._container and self._container.notifications:
            self._container.notifications.warning(title, message)
            return
        QMessageBox.warning(self, title, message)

    def _toast_err(self, title: str, message: str) -> None:
        if self._container and self._container.notifications:
            self._container.notifications.error(title, message)
            return
        QMessageBox.critical(self, title, message)

    def _build_ui(self) -> None:
        t = Tokens
        layout = self._root_layout
        layout.setContentsMargins(t.space_lg, t.space_lg, t.space_lg, t.space_lg)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        content = QWidget()
        main = QVBoxLayout(content)
        main.setSpacing(t.space_lg)

        # Заголовок и конфиг
        top = QHBoxLayout()
        top.addWidget(QLabel("Интеграции и мониторинг"))
        top.addStretch()
        export_btn = SecondaryButton("Экспорт конфигурации…")
        export_btn.setToolTip("Сохранить все настройки интеграций в JSON-файл.")
        export_btn.clicked.connect(self._export_config)
        import_btn = SecondaryButton("Импорт конфигурации…")
        import_btn.setToolTip("Загрузить настройки интеграций из JSON-файла.")
        import_btn.clicked.connect(self._import_config)
        top.addWidget(export_btn)
        top.addWidget(import_btn)
        self._btn_cancel_job = SecondaryButton("Отменить задачу")
        self._btn_cancel_job.setToolTip("Отменить текущую фоновую задачу (если поддерживается).")
        self._btn_cancel_job.setEnabled(False)
        self._btn_cancel_job.clicked.connect(self._cancel_current_job)
        top.addWidget(self._btn_cancel_job)
        main.addLayout(top)

        self._job_status = QLabel("")
        self._job_status.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px;")
        main.addWidget(self._job_status)

        self._job_log = QTextEdit()
        self._job_log.setReadOnly(True)
        self._job_log.setPlaceholderText("Логи фоновой задачи появятся здесь…")
        self._job_log.setMinimumHeight(120)
        self._job_log.setStyleSheet(
            f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; "
            f"border-radius: {t.radius_sm}px; padding: 6px; font-family: monospace; font-size: 11px;"
        )
        main.addWidget(self._job_log)

        cfg_label = QLabel(f"Файл конфигурации: {INTEGRATIONS_CONFIG_PATH}")
        cfg_label.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px;")
        cfg_label.setToolTip("Все настройки интеграций сохраняются в этот JSON-файл.")
        main.addWidget(cfg_label)

        ctx = SectionsCtx(
            parent=self,
            vm=self._vm,
            state=self._state,
            toast_ok=self._toast_ok,
            toast_err=self._toast_err,
        )

        main.addWidget(build_comet(ctx))
        main.addWidget(build_dvc(ctx))
        main.addWidget(build_sagemaker(ctx))
        main.addWidget(build_kfold(ctx))
        main.addWidget(build_tuning(ctx))
        main.addWidget(build_export(ctx))
        main.addWidget(build_sahi(ctx))
        main.addWidget(build_seg_isolation(ctx))
        main.addWidget(build_validation(ctx))
        main.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _cancel_current_job(self) -> None:
        if not self._current_job_id:
            return
        ok = self._vm.cancel_job(self._current_job_id)
        if ok:
            self._toast_warn("Отмена", "Запрошена отмена задачи…")
        else:
            self._toast_warn("Отмена", "Не удалось отменить задачу.")

    def _export_config(self) -> None:
        path = get_save_json_path(self, title="Экспорт конфигурации")
        if not path:
            return
        try:
            self._vm.export_integrations_config(path)
            self._toast_ok("Экспорт", f"Конфигурация сохранена: {path}")
        except Exception as e:
            self._toast_err("Ошибка", str(e))

    def _import_config(self) -> None:
        path = get_open_json_path(self, title="Импорт конфигурации")
        if not path:
            return
        try:
            self._vm.import_integrations_config(path)
            self._toast_ok("Импорт", "Конфигурация загружена и сохранена в приложение.")
        except Exception as e:
            self._toast_err("Ошибка", str(e))