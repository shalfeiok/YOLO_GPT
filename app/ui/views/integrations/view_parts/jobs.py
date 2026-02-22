from __future__ import annotations

from PySide6.QtCore import QTimer

from app.core.events import JobCancelled, JobFailed, JobFinished, JobLogLine, JobProgress, JobRetrying, JobStarted, JobTimedOut


class IntegrationsJobsMixin:
    def _on_job_event(self, event: object) -> None:
        QTimer.singleShot(0, lambda e=event: self._handle_job_event(e))

    def _handle_job_event(self, event: object) -> None:
        if not hasattr(self, "_job_status"):
            return
        job_id = getattr(event, "job_id", None)
        if self._current_job_id and job_id != self._current_job_id:
            return

        if isinstance(event, JobStarted):
            self._current_job_id = event.job_id
            self._job_status.setText(f"Задача: {event.name} — запуск…")
            self._btn_cancel_job.setEnabled(True)
            if hasattr(self, "_job_log"):
                self._job_log.setPlainText("")
            return
        if isinstance(event, JobProgress):
            pct = int(event.progress * 100)
            msg = f" — {event.message}" if event.message else ""
            self._job_status.setText(f"Задача: {event.name} — {pct}%{msg}")
            return
        if isinstance(event, JobRetrying):
            self._job_status.setText(f"Задача: {event.name} — повтор {event.attempt}/{event.max_attempts}: {event.error}")
            return
        if isinstance(event, JobFinished):
            self._job_status.setText(f"Задача: {event.name} — готово")
            self._btn_cancel_job.setEnabled(False)
            self._current_job_id = None
            self._handle_job_finished_toast(event)
            return
        if isinstance(event, JobFailed):
            self._job_status.setText(f"Задача: {event.name} — ошибка")
            self._btn_cancel_job.setEnabled(False)
            self._current_job_id = None
            self._toast_err("Ошибка задачи", event.error)
            return
        if isinstance(event, JobCancelled):
            self._job_status.setText(f"Задача: {event.name} — отменено")
            self._btn_cancel_job.setEnabled(False)
            self._current_job_id = None
            self._toast_warn("Отмена", "Задача отменена.")
            return
        if isinstance(event, JobTimedOut):
            self._job_status.setText(f"Задача: {event.name} — таймаут")
            self._btn_cancel_job.setEnabled(False)
            self._current_job_id = None
            self._toast_err("Таймаут", f"Превышено время: {event.timeout_sec:.1f}с")
            return
        if isinstance(event, JobLogLine) and hasattr(self, "_job_log"):
            self._append_job_log(event.line)

    def _handle_job_finished_toast(self, event: JobFinished) -> None:
        try:
            if event.name == "export_model" and event.result:
                self._toast_ok("Экспорт", f"Готово: {event.result}")
            elif event.name == "validate_model" and isinstance(event.result, dict):
                msg = "Готово.\n" + "\n".join(f"{k}: {float(v):.4f}" for k, v in event.result.items() if v is not None)
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

            logging.getLogger(__name__).debug("Integrations view update failed", exc_info=True)

    def _append_job_log(self, line: str) -> None:
        txt = self._job_log.toPlainText()
        lines = (txt.splitlines() + [line])[-400:]
        self._job_log.setPlainText("\n".join(lines))
        self._job_log.verticalScrollBar().setValue(self._job_log.verticalScrollBar().maximum())

    def _cancel_current_job(self) -> None:
        if not self._current_job_id:
            return
        if self._vm.cancel_job(self._current_job_id):
            self._toast_warn("Отмена", "Запрошена отмена задачи…")
        else:
            self._toast_warn("Отмена", "Не удалось отменить задачу.")
