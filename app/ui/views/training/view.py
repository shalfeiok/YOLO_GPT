"""
Training View: parameters, progress, metrics, console. Binds to TrainingViewModel and signals.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.ports.metrics import MetricsPort
from app.core.events.job_events import JobLogLine, JobProgress
from app.models import MODEL_HINTS, RECOMMENDED_EPOCHS, YOLO_MODEL_CHOICES
from app.ui.components.buttons import SecondaryButton
from app.ui.components.dialogs import confirm_stop_training
from app.ui.theme.tokens import Tokens
from app.ui.training.constants import MAX_DATASETS
from app.ui.training.helpers import scan_trained_weights
from app.ui.views.training.advanced_settings_dialog import AdvancedTrainingSettingsDialog
from app.ui.views.training.sections import build_training_ui
from app.ui.views.training.view_model import TrainingViewModel

if TYPE_CHECKING:
    from app.ui.infrastructure.di import Container
    from app.ui.infrastructure.signals import TrainingSignals

METRICS_UPDATE_MS = 1000


class TrainingView(QWidget):
    """Training tab: datasets, model, params, progress, metrics, console. Uses ViewModel for actions."""

    def __init__(self, container: Container, signals: TrainingSignals) -> None:
        super().__init__()
        self._container = container
        self._signals = signals
        self._metrics: MetricsPort = container.metrics
        self._vm = TrainingViewModel(container, signals)
        self._current_metrics: dict = {}
        self._metrics_start: dict = {}
        self._training_start_time: float | None = None
        self._epoch_start_time: float | None = None
        self._last_epoch: int | None = None
        self._total_epochs: int | None = None
        self._trained_choices: list[tuple[str, Path]] = []
        self._dataset_rows: list[tuple[QLabel, QLineEdit, QPushButton]] = []
        self._metrics_timer = None
        self._bus_subs: list[object] = []
        self._root_layout = QVBoxLayout(self)
        self._loading_label = QLabel("Загрузка вкладки обучения…")
        self._root_layout.addWidget(self._loading_label)
        QTimer.singleShot(0, self._init_ui_async)

    def _init_ui_async(self) -> None:
        if self._loading_label is not None:
            self._loading_label.deleteLater()
            self._loading_label = None
        self._build_ui()
        self._connect_signals()
        self._subscribe_job_logs()

    def _build_ui(self) -> None:
        build_training_ui(self)

    def _group_style(self) -> str:
        t = Tokens
        return f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}"

    def _combo_style(self) -> str:
        t = Tokens
        return f"QComboBox {{ background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 4px; min-height: 24px; }}"

    def _line_edit_style(self) -> str:
        t = Tokens
        return f"QLineEdit {{ background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 6px; }}"

    def _spin_style(self) -> str:
        t = Tokens
        return f"QSpinBox {{ background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 4px; min-width: 80px; }}"

    def _progress_style(self) -> str:
        t = Tokens
        return f"QProgressBar {{ border: 1px solid {t.border}; border-radius: {t.radius_sm}px; text-align: center; }} QProgressBar::chunk {{ background: {t.primary}; border-radius: 4px; }}"

    def refresh_theme(self) -> None:
        """Re-apply theme-dependent styles (called when theme changes)."""
        t = Tokens
        self._ds_group.setStyleSheet(self._group_style())
        self._model_group.setStyleSheet(self._group_style())
        self._params_group.setStyleSheet(self._group_style())
        self._model_combo.setStyleSheet(self._combo_style())
        self._model_hint_label.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px;")
        self._weights_edit.setStyleSheet(self._line_edit_style())
        for _lbl, edit, _btn in self._dataset_rows:
            edit.setStyleSheet(self._line_edit_style())
        self._epochs_spin.setStyleSheet(self._spin_style())
        self._epochs_recommended.setStyleSheet(f"color: {t.text_secondary};")
        self._batch_spin.setStyleSheet(self._spin_style())
        self._imgsz_spin.setStyleSheet(self._spin_style())
        self._patience_spin.setStyleSheet(self._spin_style())
        self._workers_spin.setStyleSheet(self._spin_style())
        self._optimizer_edit.setStyleSheet(self._line_edit_style())
        self._delete_cache_cb.setStyleSheet(f"color: {t.text_primary};")
        self._project_edit.setStyleSheet(self._line_edit_style())
        self._sys_metrics_label.setStyleSheet(
            f"color: {t.text_secondary}; font-size: 11px; margin-top: 4px;"
        )
        timer_style = f"color: {t.text_secondary}; font-size: 11px;"
        for w in (
            self._timer_elapsed_total,
            self._timer_elapsed_epoch,
            self._timer_eta_epoch,
            self._timer_eta_total,
        ):
            w.setStyleSheet(timer_style)
        self._progress_bar.setStyleSheet(self._progress_style())
        self._status_label.setStyleSheet(f"color: {t.text_secondary};")
        self._stats_label.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px;")
        pct_style = f"color: {t.text_secondary}; font-size: 15px; font-weight: bold;"
        for _key, w in self._metric_pct_labels.items():
            w.setStyleSheet(pct_style)
        for _key, w in self._metric_value_labels.items():
            w.setStyleSheet(
                f"color: {t.text_primary}; font-family: Consolas; font-size: 12px; min-width: 48px;"
            )
        self._metrics_dashboard.refresh_theme()

    def _add_dataset_row(self, layout: QVBoxLayout, num: int, initial: str = "") -> None:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(f"Датасет {num}:")
        lbl.setStyleSheet(f"font-weight: bold; color: {Tokens.text_primary};")
        edit = QLineEdit()
        edit.setText(initial)
        edit.setToolTip(
            "Путь к папке датасета (с data.yaml и подпапками train/valid или train/val)."
        )
        edit.setStyleSheet(self._line_edit_style())
        btn = SecondaryButton("…")
        btn.setToolTip("Выбрать папку датасета")
        idx = len(self._dataset_rows)
        btn.clicked.connect(lambda: self._browse_dataset(idx))
        row_layout.addWidget(lbl)
        row_layout.addWidget(edit, 1)
        row_layout.addWidget(btn)
        layout.insertWidget(layout.count() - 1, row)
        self._dataset_rows.append((lbl, edit, btn))

    def _on_add_dataset(self) -> None:
        if len(self._dataset_rows) >= MAX_DATASETS:
            return
        ds_group = self._add_ds_btn.parent()
        layout = ds_group.layout()
        n = len(self._dataset_rows) + 1
        self._add_dataset_row(layout, n, "")

    def _get_dataset_paths(self) -> list[Path]:
        paths = []
        for _, edit, _ in self._dataset_rows:
            p = edit.text().strip()
            if p and Path(p).is_dir():
                paths.append(Path(p))
        return paths

    def _browse_dataset(self, index: int) -> None:
        if index < 0 or index >= len(self._dataset_rows):
            return
        _, edit, _ = self._dataset_rows[index]
        path = QFileDialog.getExistingDirectory(self, "Выберите папку датасета", edit.text())
        if path:
            edit.setText(path)

    def _model_values(self) -> list[str]:
        labels = [m.label for m in YOLO_MODEL_CHOICES]
        self._trained_choices = scan_trained_weights(self._container.project_root)
        if self._trained_choices:
            labels.append("—— Дообучение ——")
            labels.extend(t[0] for t in self._trained_choices)
        labels.append("Наша модель (файл…)…")
        return labels

    def _refresh_model_list(self) -> None:
        self._model_combo.clear()
        self._model_combo.addItems(self._model_values())

    def _get_model_id_for_choice(self, choice: str) -> str | None:
        for m in YOLO_MODEL_CHOICES:
            if m.label == choice:
                return m.model_id
        return None

    def _get_recommended_epochs(self, model_id: str) -> tuple[int, int]:
        for suffix in ("n", "s", "m", "l", "x", "c", "e"):
            if model_id.endswith(f"{suffix}.pt"):
                return RECOMMENDED_EPOCHS.get(suffix, (100, 300))
        return (100, 300)

    def _on_model_changed(self, choice: str) -> None:
        if choice == "Наша модель (файл…)…":
            self._weights_frame.show()
            self._model_hint_label.setText("Укажите путь к своим весам (.pt) для дообучения.")
            self._epochs_recommended.setText("")
        else:
            self._weights_frame.hide()
            model_id = self._get_model_id_for_choice(choice)
            if model_id:
                self._model_hint_label.setText(MODEL_HINTS.get(model_id, ""))
                low, high = self._get_recommended_epochs(model_id)
                self._epochs_recommended.setText(f"(рекомендуется {low}–{high})")
            else:
                self._model_hint_label.setText("")
                self._epochs_recommended.setText("")

    def _get_model_id_and_weights(self) -> tuple[str, Path | None]:
        choice = self._model_combo.currentText()
        if choice == "Наша модель (файл…)…":
            p = self._weights_edit.text().strip()
            if p and Path(p).exists():
                return ("", Path(p))
            return (YOLO_MODEL_CHOICES[0].model_id, None)
        for label, path in self._trained_choices:
            if choice == label:
                return ("", path)
        for m in YOLO_MODEL_CHOICES:
            if m.label == choice:
                return (m.model_id, None)
        return (YOLO_MODEL_CHOICES[0].model_id, None)

    def _browse_weights(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите веса (.pt)",
            self._project_edit.text(),
            "PyTorch (*.pt);;Все файлы (*.*)",
        )
        if path:
            self._weights_edit.setText(path)

    def _browse_project(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Папка для runs", self._project_edit.text())
        if path:
            self._project_edit.setText(path)

    def _delete_old_runs(self) -> None:
        p = Path(self._project_edit.text().strip())
        if not p.is_dir():
            QMessageBox.critical(self, "Ошибка", "Укажите существующую папку runs.")
            return
        try:
            children = list(p.iterdir())
        except OSError as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать папку: {e}")
            return
        if not children:
            QMessageBox.information(self, "Удаление", "Папка уже пуста.")
            return
        reply = QMessageBox.question(
            self,
            "Удалить старые runs?",
            f"Будет удалено содержимое папки:\n{p}\n\nПродолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        errs = []
        for child in children:
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            except OSError as e:
                errs.append(f"{child.name}: {e}")
        if errs:
            QMessageBox.critical(self, "Ошибка", "Не удалось удалить:\n" + "\n".join(errs[:5]))
        else:
            QMessageBox.information(self, "Готово", "Содержимое папки runs удалено.")

    def _start_metrics_timer(self) -> None:
        from PySide6.QtCore import QTimer

        self._metrics_timer = QTimer(self)
        self._metrics_timer.timeout.connect(self._tick_system_metrics)
        self._metrics_timer.start(METRICS_UPDATE_MS)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        if seconds < 0 or not (seconds < 1e9):
            return "—"
        s = int(round(seconds))
        if s < 60:
            return f"0:{s:02d}"
        m, s = divmod(s, 60)
        if m < 60:
            return f"{m}:{s:02d}"
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}"

    def _tick_system_metrics(self) -> None:
        try:
            cpu = self._metrics.get_cpu_percent()
            used_gb, total_gb = self._metrics.get_memory_info()
            ram_s = f"RAM: {used_gb:.1f}/{total_gb:.1f} GB"
            cpu_s = f"CPU: {cpu:.0f}%"
            gpu_info = self._metrics.get_gpu_info()
            if gpu_info:
                gpu_s = f"GPU: {gpu_info['util']:.0f}%"
                if gpu_info.get("temp"):
                    gpu_s += f" {gpu_info['temp']}°C"
                gpu_s += f" ({gpu_info['mem_used_mb']:.0f}/{gpu_info['mem_total_mb']:.0f} MB)"
            else:
                gpu_s = "GPU: —"
            self._sys_metrics_label.setText(f"  {cpu_s}  |  {ram_s}  |  {gpu_s}")
        except KeyboardInterrupt:
            raise
        except Exception:
            self._sys_metrics_label.setText("CPU: —  RAM: —  GPU: —")
        # Таймеры
        if self._training_start_time is None:
            self._timer_elapsed_total.setText("—")
            self._timer_elapsed_epoch.setText("—")
            self._timer_eta_epoch.setText("—")
            self._timer_eta_total.setText("—")
            return
        now = time.time()
        elapsed_total = now - self._training_start_time
        self._timer_elapsed_total.setText(self._format_duration(elapsed_total))
        if self._epoch_start_time is not None:
            elapsed_epoch = now - self._epoch_start_time
            self._timer_elapsed_epoch.setText(self._format_duration(elapsed_epoch))
            m = self._current_metrics
            batch_pct = m.get("batch_pct")
            epoch = m.get("epoch")
            epoch_total = m.get("epoch_total") or self._total_epochs
            if batch_pct is not None and batch_pct > 0:
                eta_epoch_sec = elapsed_epoch * (100 - batch_pct) / batch_pct
                self._timer_eta_epoch.setText(self._format_duration(eta_epoch_sec))
            else:
                self._timer_eta_epoch.setText("—")
            if epoch is not None and epoch_total is not None and epoch_total > 0:
                progress = (epoch - 1) + (batch_pct or 0) / 100.0
                if progress > 0:
                    eta_total_sec = elapsed_total * (epoch_total - progress) / progress
                    self._timer_eta_total.setText(self._format_duration(max(0, eta_total_sec)))
                else:
                    self._timer_eta_total.setText("—")
            else:
                self._timer_eta_total.setText("—")
        else:
            self._timer_elapsed_epoch.setText("—")
            self._timer_eta_epoch.setText("—")
            self._timer_eta_total.setText("—")

    def _subscribe_job_logs(self) -> None:
        bus = self._container.event_bus
        self._bus_subs.append(bus.subscribe_weak(JobLogLine, self._on_job_log_line))
        self._bus_subs.append(bus.subscribe_weak(JobProgress, self._on_job_progress))

    def _on_job_progress(self, event: JobProgress) -> None:
        if getattr(self._vm, "_active_job_id", None) != event.job_id or event.name != "training":
            return
        self._on_progress(event.progress, event.message or "")

    def _on_job_log_line(self, event: JobLogLine) -> None:
        if getattr(self._vm, "_active_job_id", None) != event.job_id or event.name != "training":
            return
        self._on_console_lines_batch(event.line.splitlines())

    def _connect_signals(self) -> None:
        self._signals.progress_updated.connect(self._on_progress)
        self._signals.console_lines_batch.connect(self._on_console_lines_batch)
        self._signals.training_finished.connect(self._on_training_finished)

    def _on_progress(self, pct: float, msg: str) -> None:
        if pct >= 0:
            self._progress_bar.setValue(int(pct * 1000))
        self._status_label.setText(msg)

    def _on_console_lines_batch(self, lines: list[str]) -> None:
        for line in lines:
            parsed = self._vm.parse_metrics_from_line(line)
            if parsed:
                self._current_metrics.update(parsed)
                self._update_metrics_display()

    def _update_metrics_display(self) -> None:
        m = self._current_metrics
        for key in ("box_loss", "cls_loss", "dfl_loss", "size", "gpu_mem", "instances"):
            v = m.get(key)
            if v is not None and key not in self._metrics_start:
                self._metrics_start[key] = float(v) if isinstance(v, (int, float)) else v
        epoch = m.get("epoch")
        epoch_total = m.get("epoch_total")
        if epoch is not None and epoch != self._last_epoch:
            self._epoch_start_time = time.time()
            self._last_epoch = epoch
        ep_str = f"{epoch}/{epoch_total}" if epoch is not None and epoch_total is not None else "—"
        gpu = m.get("gpu_mem")
        if isinstance(gpu, float):
            gpu_s = f"{gpu:.1f}G"
        elif isinstance(gpu, int):
            gpu_s = f"{gpu}M" if gpu < 1000 else f"{gpu / 1024:.1f}G"
        else:
            gpu_s = "—"
        box = m.get("box_loss")
        cls = m.get("cls_loss")
        dfl = m.get("dfl_loss")
        inst = m.get("instances", "—")
        sz = m.get("size")
        for key, val in [
            ("epoch", ep_str),
            ("gpu_mem", gpu_s),
            ("box_loss", f"{box:.3f}" if isinstance(box, (int, float)) else "—"),
            ("cls_loss", f"{cls:.3f}" if isinstance(cls, (int, float)) else "—"),
            ("dfl_loss", f"{dfl:.3f}" if isinstance(dfl, (int, float)) else "—"),
            ("instances", str(inst)),
            ("size", f"{sz:.1f}" if isinstance(sz, (int, float)) else "—"),
        ]:
            if key in self._metric_value_labels:
                self._metric_value_labels[key].setText(str(val))
        for key, cur in [("box_loss", box), ("cls_loss", cls), ("dfl_loss", dfl)]:
            pct_text = ""
            if isinstance(cur, (int, float)):
                start_val = self._metrics_start.get(key)
                if start_val is not None and start_val != 0:
                    pct = ((cur - start_val) / start_val) * 100
                    sign = "↓" if pct < 0 else "↑"
                    pct_text = f"{sign}{abs(pct):.0f}%"
            if key in self._metric_pct_labels:
                self._metric_pct_labels[key].setText(pct_text)
        batch_pct = m.get("batch_pct")
        stats = f"Эпоха {ep_str}"
        if batch_pct is not None:
            stats += f"  ·  батч {batch_pct}%"
        self._stats_label.setText(stats)
        self._metrics_dashboard.push_metrics(m)

    def _on_training_finished(self, best_path: Path | None, error: str | None) -> None:
        self._training_start_time = None
        self._epoch_start_time = None
        self._current_metrics.clear()
        self._metrics_start.clear()
        self._timer_elapsed_total.setText("—")
        self._timer_elapsed_epoch.setText("—")
        self._timer_eta_epoch.setText("—")
        self._timer_eta_total.setText("—")
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        if error:
            self._status_label.setText(f"Ошибка: {error}")
            self._progress_bar.setValue(0)
            if self._container.notifications:
                self._container.notifications.error(error)
            else:
                QMessageBox.critical(self, "Ошибка обучения", error)
            return
        self._progress_bar.setValue(1000)
        self._status_label.setText(f"Обучение завершено. Веса: {best_path}")
        self._refresh_model_list()

    def _on_stop_clicked(self) -> None:
        confirm_stop_training(self.window(), self._vm.stop_training)

    def _open_advanced_settings(self) -> None:
        dlg = AdvancedTrainingSettingsDialog(self._advanced_options, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._advanced_options = dlg.get_values()

    def _start_training(self) -> None:
        dataset_paths = self._get_dataset_paths()
        if not dataset_paths:
            msg = "Укажите хотя бы один датасет (папку с data.yaml и train/valid)."
            if self._container.notifications:
                self._container.notifications.warning(msg)
            else:
                QMessageBox.critical(self, "Ошибка", msg)
            return
        project = Path(self._project_edit.text().strip())
        combined_dir = project.parent / "combined_dataset"
        out_yaml = combined_dir / "data.yaml"
        try:
            self._container.dataset_builder.build_multi(dataset_paths, out_yaml)
        except Exception as e:
            msg = f"Не удалось собрать датасет: {e}"
            if self._container.notifications:
                self._container.notifications.error(msg)
            else:
                QMessageBox.critical(self, "Ошибка", msg)
            return
        if self._delete_cache_cb.isChecked():
            for base in dataset_paths:
                for sub in ("train", "valid", "val"):
                    cache = base / sub / "labels.cache"
                    if cache.exists():
                        try:
                            cache.unlink()
                        except OSError:
                            pass
        out_yaml = out_yaml.resolve()
        model_id, weights_path = self._get_model_id_and_weights()
        if not model_id and not weights_path:
            msg = "Выберите базовую модель или укажите путь к весам (.pt)."
            if self._container.notifications:
                self._container.notifications.warning(msg)
            else:
                QMessageBox.critical(self, "Ошибка", msg)
            return
        epochs = self._epochs_spin.value()
        batch = self._batch_spin.value()
        imgsz = self._imgsz_spin.value()
        patience = self._patience_spin.value()
        workers = self._workers_value()
        optimizer = self._optimizer_value()
        from datetime import datetime

        log_dir = project / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._progress_bar.setValue(0)
        self._current_metrics = {}
        self._metrics_start = {}
        self._training_start_time = time.time()
        self._total_epochs = epochs
        self._epoch_start_time = None
        self._last_epoch = None
        self._metrics_dashboard.clear()
        self._vm.start_training(
            data_yaml=out_yaml,
            model_name=model_id or "yolo11n.pt",
            epochs=epochs,
            batch=batch,
            imgsz=imgsz,
            device="",
            patience=patience,
            project=project,
            weights_path=weights_path,
            workers=workers,
            optimizer=optimizer,
            log_path=log_path,
            advanced_options=self._advanced_options,
        )

    def _workers_value(self) -> int:
        return self._workers_spin.value()

    def _optimizer_value(self) -> str:
        return self._optimizer_edit.text().strip()

    def shutdown(self) -> None:
        self._vm.stop_training()
        bus = self._container.event_bus
        for sub in self._bus_subs:
            bus.unsubscribe(sub)
        self._bus_subs.clear()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.shutdown()
        super().closeEvent(event)
