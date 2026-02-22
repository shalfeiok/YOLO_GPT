"""
Training ViewModel: starts/stops training via ITrainer, bridges progress and console to signals.
Does not hold UI; View subscribes to signals and calls start_training/stop_training.
"""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer

from app.application.use_cases.train_model import TrainModelRequest
from app.console_redirect import strip_ansi
from app.core.events import TrainingCancelled, TrainingFailed, TrainingFinished, TrainingProgress
from app.core.events.job_events import (
    JobCancelled,
    JobFailed,
    JobFinished,
    JobLogLine,
    JobProgress,
    JobStarted,
)
from app.core.observability.run_manifest import register_run
from app.training_metrics import parse_metrics_line, parse_progress_line

if TYPE_CHECKING:
    from app.ui.infrastructure.di import Container
    from app.ui.infrastructure.signals import TrainingSignals

CONSOLE_POLL_MS = 80
CONSOLE_BATCH_MAX = 100  # emit up to this many lines per poll to reduce signal traffic
JOB_PROGRESS_MIN_INTERVAL_S = 0.15
MAX_SAME_LOG_LINE_STREAK = 3

log = logging.getLogger(__name__)


class TrainingViewModel(QObject):
    """Coordinates training: runs trainer in worker thread, polls console queue, emits signals."""

    def __init__(self, container: Container, signals: TrainingSignals) -> None:
        super().__init__()
        self._container = container
        self._signals = signals
        self._training_thread: Thread | None = None
        self._console_queue: Queue | None = None
        self._console_timer = QTimer(self)
        self._console_timer.timeout.connect(self._poll_console)
        self._log_file = None
        self._active_job_id: str | None = None
        self._last_job_progress_ts: float = 0.0
        self._last_job_progress_key: tuple[int, str] | None = None
        self._last_log_line: str | None = None
        self._last_log_repeat_count = 0

        # Subscribe UI to application events via EventBus.
        self._subs = []
        bus = self._container.event_bus
        self._subs.append(bus.subscribe(TrainingProgress, self._on_training_progress))
        self._subs.append(bus.subscribe(TrainingFinished, self._on_training_finished))
        self._subs.append(bus.subscribe(TrainingFailed, self._on_training_failed))
        self._subs.append(bus.subscribe(TrainingCancelled, self._on_training_cancelled))

    def _emit_on_ui_thread(self, fn) -> None:
        # Event handlers may run in a worker thread; re-dispatch to Qt main loop.
        QTimer.singleShot(0, fn)

    def _on_training_progress(self, ev: TrainingProgress) -> None:
        if self._active_job_id:
            now = time.monotonic()
            progress_key = (int(ev.fraction * 1000), str(ev.message or ""))
            should_emit = (
                self._last_job_progress_key != progress_key
                or (now - self._last_job_progress_ts) >= JOB_PROGRESS_MIN_INTERVAL_S
            )
            if should_emit:
                self._container.event_bus.publish(
                    JobProgress(
                        job_id=self._active_job_id,
                        name="training",
                        progress=ev.fraction,
                        message=ev.message,
                    )
                )
                self._last_job_progress_ts = now
                self._last_job_progress_key = progress_key
        self._emit_on_ui_thread(
            lambda: self._signals.progress_updated.emit(ev.fraction, ev.message)
        )

    def _on_training_finished(self, ev: TrainingFinished) -> None:
        if self._active_job_id:
            self._container.event_bus.publish(
                JobProgress(
                    job_id=self._active_job_id, name="training", progress=1.0, message="finished"
                )
            )
            self._container.event_bus.publish(
                JobFinished(job_id=self._active_job_id, name="training", result=None)
            )
            self._active_job_id = None
        self._emit_on_ui_thread(
            lambda: self._signals.training_finished.emit(ev.best_weights_path, None)
        )

    def _on_training_failed(self, ev: TrainingFailed) -> None:
        self._join_training_thread_async()
        if self._active_job_id:
            self._container.event_bus.publish(
                JobFailed(job_id=self._active_job_id, name="training", error=str(ev.error))
            )
            self._active_job_id = None
        self._emit_on_ui_thread(lambda: self._signals.training_finished.emit(None, str(ev.error)))

    def _on_training_cancelled(self, ev: TrainingCancelled) -> None:
        self._join_training_thread_async()
        if self._active_job_id:
            self._container.event_bus.publish(
                JobCancelled(job_id=self._active_job_id, name="training")
            )
            self._active_job_id = None
        self._emit_on_ui_thread(lambda: self._signals.training_finished.emit(None, ev.message))

    def start_training(
        self,
        data_yaml: Path,
        model_name: str,
        epochs: int,
        batch: int,
        imgsz: int,
        device: str,
        patience: int,
        project: Path,
        weights_path: Path | None,
        workers: int,
        optimizer: str,
        log_path: Path | None,
        advanced_options: dict | None = None,
    ) -> None:
        """Start training in background. Progress and console lines are emitted via signals."""
        self._console_queue = Queue()
        if log_path:
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                self._log_file = open(log_path, "w", encoding="utf-8")
                self._log_file.write("Лог обучения\n")
            except Exception:
                self._log_file = None
        else:
            self._log_file = None

        train_uc = self._container.train_model_use_case
        self._active_job_id = uuid.uuid4().hex
        self._last_job_progress_ts = 0.0
        self._last_job_progress_key = None
        self._last_log_line = None
        self._last_log_repeat_count = 0
        self._container.event_bus.publish(JobStarted(job_id=self._active_job_id, name="training"))
        self._container.event_bus.publish(
            JobProgress(
                job_id=self._active_job_id, name="training", progress=0.0, message="started"
            )
        )
        try:
            register_run(
                job_id=self._active_job_id,
                run_type="training",
                spec={
                    "data_yaml": str(data_yaml),
                    "model_name": model_name,
                    "epochs": epochs,
                    "batch": batch,
                    "imgsz": imgsz,
                    "device": device,
                    "patience": patience,
                    "project": str(project),
                    "weights_path": None if weights_path is None else str(weights_path),
                    "workers": workers,
                    "optimizer": optimizer,
                    "advanced_options": advanced_options or {},
                },
                artifacts={
                    "project_dir": str(project),
                    "log_path": None if log_path is None else str(log_path),
                },
            )
        except Exception:
            log.exception("Failed to create training run manifest")

        def run() -> None:
            try:
                req = TrainModelRequest(
                    data_yaml=data_yaml,
                    model_name=model_name,
                    epochs=epochs,
                    batch=batch,
                    imgsz=imgsz,
                    device=device,
                    patience=patience,
                    project=project,
                    weights_path=weights_path,
                    workers=workers,
                    optimizer=optimizer,
                    advanced_options=advanced_options or {},
                )
                # Progress/result are delivered via the EventBus subscriptions above.
                train_uc.execute(req, on_progress=None, console_queue=self._console_queue)
                self._console_queue.put(None)
            except Exception:
                # The use-case will publish TrainingFailed; this catch is only to stop console polling.
                log.exception("Unhandled exception in training worker thread")
                try:
                    self._console_queue.put(None)
                except Exception:
                    import logging

                    logging.getLogger(__name__).debug(
                        "Training view-model cleanup failed", exc_info=True
                    )
            finally:
                # Ensure console polling can stop.
                try:
                    self._console_queue.put(None)
                except Exception:
                    import logging

                    logging.getLogger(__name__).debug(
                        "Training view-model cleanup failed", exc_info=True
                    )

        self._training_thread = Thread(target=run, daemon=False)
        self._training_thread.start()
        self._console_timer.start(CONSOLE_POLL_MS)

    def _join_training_thread_async(self) -> None:
        """Join the training thread without blocking the UI thread."""
        t = self._training_thread
        if t is None:
            return

        def joiner() -> None:
            try:
                t.join(timeout=30)
            except Exception:
                log.exception("Failed joining training thread")
            finally:
                # Don't keep a dead thread reference.
                if self._training_thread is t and not t.is_alive():
                    self._training_thread = None

        Thread(target=joiner, daemon=True).start()

    def _poll_console(self) -> None:
        if self._console_queue is None:
            return
        batch: list[str] = []
        try:
            while len(batch) < CONSOLE_BATCH_MAX:
                line = self._console_queue.get_nowait()
                if line is None:
                    self._console_timer.stop()
                    if self._log_file:
                        try:
                            self._log_file.close()
                        except Exception:
                            import logging

                            logging.getLogger(__name__).debug(
                                "Training view-model cleanup failed", exc_info=True
                            )
                        self._log_file = None
                    self._console_queue = None
                    if batch:
                        self._signals.console_lines_batch.emit(batch)
                    return
                clean_line = strip_ansi(line)
                batch.append(clean_line)
                if self._active_job_id and self._should_publish_log_line(clean_line):
                    self._container.event_bus.publish(
                        JobLogLine(job_id=self._active_job_id, name="training", line=clean_line)
                    )
                if self._log_file:
                    try:
                        self._log_file.write(line + "\n")
                        self._log_file.flush()
                    except Exception:
                        import logging

                        logging.getLogger(__name__).debug(
                            "Training view-model cleanup failed", exc_info=True
                        )
        except Empty:
            pass
        if batch:
            self._signals.console_lines_batch.emit(batch)

    def stop_training(self) -> None:
        self._container.train_model_use_case.stop()
        self._join_training_thread_async()

    def _should_publish_log_line(self, line: str) -> bool:
        if line == self._last_log_line:
            self._last_log_repeat_count += 1
        else:
            self._last_log_line = line
            self._last_log_repeat_count = 1
        return self._last_log_repeat_count <= MAX_SAME_LOG_LINE_STREAK

    def parse_metrics_from_line(self, line: str) -> dict | None:
        """Return parsed metrics dict from a console line, or None."""
        return parse_metrics_line(line) or parse_progress_line(line)
