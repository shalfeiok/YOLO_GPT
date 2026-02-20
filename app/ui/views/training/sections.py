"""UI sections builder for TrainingView.

This module exists to keep TrainingView (controller/binding code) small.
"""
from __future__ import annotations

import os
from app.core.paths import PROJECT_ROOT
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.config import (
    DEFAULT_BATCH,
    DEFAULT_DATASET1,
    DEFAULT_EPOCHS,
    DEFAULT_IMGSZ,
    DEFAULT_PATIENCE,
    DEFAULT_WORKERS,
)
from app.models import MODEL_HINTS, RECOMMENDED_EPOCHS, YOLO_MODEL_CHOICES
from app.ui.training.constants import MAX_DATASETS, METRICS_HEADERS_RU, METRICS_TOOLTIP_RU_BASE
from app.ui.theme.tokens import Tokens
from app.ui.components.buttons import PrimaryButton, SecondaryButton
from app.ui.components.cards import Card
from app.ui.components.inputs import NoWheelSpinBox
from app.ui.components.log_view import LogView
from app.ui.views.metrics.dashboard import MetricsDashboardWidget

if TYPE_CHECKING:
    from app.ui.views.training.view import TrainingView


def build_training_ui(view: TrainingView) -> None:
    t = Tokens
    layout = QVBoxLayout(view)
    layout.setContentsMargins(t.space_lg, t.space_lg, t.space_lg, t.space_lg)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(scroll.Shape.NoFrame)
    scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
    content = QWidget()
    main_layout = QVBoxLayout(content)
    main_layout.setSpacing(t.space_lg)

    # Datasets
    view._ds_group = QGroupBox("Датасеты")
    view._ds_group.setStyleSheet(view._group_style())
    ds_layout = QVBoxLayout(view._ds_group)
    view._add_dataset_row(ds_layout, 1, str(DEFAULT_DATASET1))
    view._add_ds_btn = SecondaryButton("+ Добавить датасет")
    view._add_ds_btn.setToolTip("Добавить ещё один датасет для объединённого обучения.")
    view._add_ds_btn.clicked.connect(view._on_add_dataset)
    ds_layout.addWidget(view._add_ds_btn)
    main_layout.addWidget(view._ds_group)

    # Model
    view._model_group = QGroupBox("Модель")
    view._model_group.setStyleSheet(view._group_style())
    model_layout = QFormLayout(view._model_group)
    view._model_combo = QComboBox()
    view._model_combo.setMinimumHeight(32)
    view._model_combo.setStyleSheet(view._combo_style())
    view._refresh_model_list()
    view._model_combo.setToolTip("Базовая архитектура модели YOLO (n/s/m/l/x). От неё зависят скорость и точность.")
    view._model_combo.currentTextChanged.connect(view._on_model_changed)
    model_layout.addRow("Модель:", view._model_combo)
    view._model_hint_label = QLabel("")
    view._model_hint_label.setWordWrap(True)
    view._model_hint_label.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px;")
    model_layout.addRow("", view._model_hint_label)
    view._weights_frame = QWidget()
    weights_layout = QHBoxLayout(view._weights_frame)
    weights_layout.setContentsMargins(0, 0, 0, 0)
    view._weights_edit = QLineEdit()
    view._weights_edit.setPlaceholderText("Путь к весам (.pt)")
    view._weights_edit.setToolTip("Путь к файлу весов .pt для дообучения (fine-tuning). Оставьте пустым для обучения с нуля выбранной модели.")
    view._weights_edit.setStyleSheet(view._line_edit_style())
    view._browse_weights_btn = SecondaryButton("Обзор…")
    view._browse_weights_btn.setToolTip("Выбрать файл весов (.pt)")
    view._browse_weights_btn.clicked.connect(view._browse_weights)
    weights_layout.addWidget(view._weights_edit)
    weights_layout.addWidget(view._browse_weights_btn)
    model_layout.addRow("Путь к весам:", view._weights_frame)
    view._weights_frame.hide()
    main_layout.addWidget(view._model_group)

    # Params
    view._params_group = QGroupBox("Параметры обучения")
    view._params_group.setStyleSheet(view._group_style())
    params_layout = QFormLayout(view._params_group)
    view._epochs_spin = NoWheelSpinBox()
    view._epochs_spin.setRange(1, 10000)
    view._epochs_spin.setValue(DEFAULT_EPOCHS)
    view._epochs_spin.setToolTip("Число эпох обучения (1–10000). Больше эпох — дольше обучение, обычно лучше сходимость.")
    view._epochs_spin.setStyleSheet(view._spin_style())
    params_layout.addRow("Эпохи:", view._epochs_spin)
    view._epochs_recommended = QLabel("")
    view._epochs_recommended.setStyleSheet(f"color: {t.text_secondary};")
    params_layout.addRow("", view._epochs_recommended)
    view._batch_spin = NoWheelSpinBox()
    view._batch_spin.setRange(-1, 256)
    view._batch_spin.setValue(DEFAULT_BATCH)
    view._batch_spin.setSpecialValueText("авто")
    view._batch_spin.setToolTip("Размер батча: -1 = авто (рекомендуется), иначе 1–256. Больше батч — быстрее на GPU, но нужно больше видеопамяти.")
    view._batch_spin.setStyleSheet(view._spin_style())
    params_layout.addRow("Batch:", view._batch_spin)
    view._imgsz_spin = NoWheelSpinBox()
    view._imgsz_spin.setRange(64, 2048)
    view._imgsz_spin.setValue(DEFAULT_IMGSZ)
    view._imgsz_spin.setToolTip("Размер стороны входного изображения в пикселях (64–2048). 640 — стандарт для YOLO.")
    view._imgsz_spin.setStyleSheet(view._spin_style())
    params_layout.addRow("Размер изображения:", view._imgsz_spin)
    view._patience_spin = NoWheelSpinBox()
    view._patience_spin.setRange(1, 1000)
    view._patience_spin.setValue(DEFAULT_PATIENCE)
    view._patience_spin.setToolTip("Early stopping: остановить обучение, если метрика не улучшалась столько эпох подряд.")
    view._patience_spin.setStyleSheet(view._spin_style())
    params_layout.addRow("Patience:", view._patience_spin)
    view._workers_spin = NoWheelSpinBox()
    view._workers_spin.setRange(0, 32)
    default_workers = min(32, os.cpu_count() or 8)
    view._workers_spin.setValue(default_workers)
    view._workers_spin.setSpecialValueText("гл. поток")
    view._workers_spin.setToolTip("Число потоков загрузки данных (по умолчанию = число ядер CPU). 0 = только главный поток; больше — быстрее загрузка, но выше нагрузка на CPU/RAM.")
    view._workers_spin.setStyleSheet(view._spin_style())
    params_layout.addRow("Workers:", view._workers_spin)
    view._optimizer_edit = QLineEdit()
    view._optimizer_edit.setPlaceholderText("авто")
    view._optimizer_edit.setStyleSheet(view._line_edit_style())
    view._optimizer_edit.setToolTip("SGD, Adam, AdamW или пусто (авто)")
    params_layout.addRow("Optimizer:", view._optimizer_edit)
    view._delete_cache_cb = QCheckBox("Удалять кэш датасета перед обучением")
    view._delete_cache_cb.setChecked(True)
    view._delete_cache_cb.setToolTip("Если включено: перед каждым запуском удаляются labels.cache в train/valid, чтобы Ultralytics пересоздал кэш. Выключите для повторных запусков без смены данных (быстрее старт).")
    view._delete_cache_cb.setStyleSheet(f"color: {t.text_primary};")
    params_layout.addRow(view._delete_cache_cb)
    main_layout.addWidget(view._params_group)

    # Project dir
    proj_layout = QHBoxLayout()
    proj_lbl = QLabel("Папка runs:")
    proj_lbl.setToolTip("Каталог, куда сохраняются логи и веса обучения (runs/train/...).")
    proj_layout.addWidget(proj_lbl)
    view._project_edit = QLineEdit()
    view._project_edit.setText(str(PROJECT_ROOT / "runs" / "train"))
    view._project_edit.setToolTip("Путь к папке runs для сохранения результатов обучения.")
    view._project_edit.setStyleSheet(view._line_edit_style())
    proj_layout.addWidget(view._project_edit, 1)
    view._browse_project_btn = SecondaryButton("…")
    view._browse_project_btn.setToolTip("Выбрать папку для runs")
    view._browse_project_btn.clicked.connect(view._browse_project)
    view._delete_runs_btn = SecondaryButton("Удалить старые runs")
    view._delete_runs_btn.setToolTip("Удалить предыдущие запуски обучения в этой папке (освободить место).")
    view._delete_runs_btn.clicked.connect(view._delete_old_runs)
    proj_layout.addWidget(view._browse_project_btn)
    proj_layout.addWidget(view._delete_runs_btn)
    main_layout.addLayout(proj_layout)

    # Progress
    view._progress_bar = QProgressBar()
    view._progress_bar.setRange(0, 1000)
    view._progress_bar.setValue(0)
    view._progress_bar.setTextVisible(True)
    view._progress_bar.setStyleSheet(view._progress_style())
    main_layout.addWidget(view._progress_bar)
    view._status_label = QLabel("Готово к обучению.")
    view._status_label.setStyleSheet(f"color: {t.text_secondary};")
    main_layout.addWidget(view._status_label)
    view._stats_label = QLabel("")
    view._stats_label.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px;")
    main_layout.addWidget(view._stats_label)

    # Расширенные настройки (по центру над Старт/Стоп)
    view._advanced_options: dict = {}
    adv_btn_layout = QHBoxLayout()
    adv_btn_layout.addStretch()
    view._advanced_btn = SecondaryButton("Расширенные настройки обучения")
    view._advanced_btn.setToolTip("Аугментация Albumentations, кэш, lr, mosaic, mixup, seed, веса потерь и др. Пресеты и профили.")
    view._advanced_btn.clicked.connect(view._open_advanced_settings)
    adv_btn_layout.addWidget(view._advanced_btn)
    adv_btn_layout.addStretch()
    main_layout.addLayout(adv_btn_layout)

    # Buttons
    btn_layout = QHBoxLayout()
    view._start_btn = PrimaryButton("Старт обучения")
    view._start_btn.setToolTip("Запустить обучение модели по выбранным датасетам и параметрам")
    view._start_btn.clicked.connect(view._start_training)
    view._stop_btn = SecondaryButton("Стоп")
    view._stop_btn.setToolTip("Остановить обучение (будет запрошено подтверждение)")
    view._stop_btn.setEnabled(False)
    view._stop_btn.clicked.connect(view._on_stop_clicked)
    btn_layout.addWidget(view._start_btn)
    btn_layout.addWidget(view._stop_btn)
    main_layout.addLayout(btn_layout)

    # Metrics block: заголовки → значения → под полями box/cls/dfl — проценты (крупнее)
    metrics_card = Card(view)
    metrics_card.setToolTip(METRICS_TOOLTIP_RU_BASE)
    metrics_ly = metrics_card.layout()
    title_metrics = QLabel("Показатели обучения")
    title_metrics.setStyleSheet(f"font-weight: bold; color: {t.text_primary}; font-size: 13px;")
    metrics_ly.addWidget(title_metrics)
    grid = QGridLayout()
    view._metric_value_labels: dict[str, QLabel] = {}
    view._metric_pct_labels: dict[str, QLabel] = {}  # box_loss, cls_loss, dfl_loss — под полем
    key_map = ("epoch", "gpu_mem", "box_loss", "cls_loss", "dfl_loss", "instances", "size")
    pct_style = f"color: {t.text_secondary}; font-size: 15px; font-weight: bold;"
    for col, (name, key) in enumerate(zip(METRICS_HEADERS_RU, key_map)):
        lbl = QLabel(name + ":")
        lbl.setStyleSheet(f"color: {t.text_secondary}; font-size: 12px;")
        grid.addWidget(lbl, 0, col)
        val = QLabel("—")
        val.setStyleSheet(f"color: {t.text_primary}; font-family: Consolas; font-size: 12px; min-width: 48px;")
        view._metric_value_labels[key] = val
        grid.addWidget(val, 1, col)
        if key in ("box_loss", "cls_loss", "dfl_loss"):
            pct_lbl = QLabel("")
            pct_lbl.setStyleSheet(pct_style)
            view._metric_pct_labels[key] = pct_lbl
            grid.addWidget(pct_lbl, 2, col)
    metrics_ly.addLayout(grid)
    # CPU / RAM / GPU внутри карточки
    view._sys_metrics_label = QLabel("CPU: —  RAM: —  GPU: —")
    view._sys_metrics_label.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px; margin-top: 4px;")
    view._sys_metrics_label.setToolTip("Загрузка системы во время обучения.")
    metrics_ly.addWidget(view._sys_metrics_label)
    # Таймеры
    timer_style = f"color: {t.text_secondary}; font-size: 11px;"
    metrics_ly.addWidget(QLabel("Таймеры:"))
    timer_grid = QGridLayout()
    view._timer_elapsed_total = QLabel("—")
    view._timer_elapsed_total.setStyleSheet(timer_style)
    view._timer_elapsed_epoch = QLabel("—")
    view._timer_elapsed_epoch.setStyleSheet(timer_style)
    view._timer_eta_epoch = QLabel("—")
    view._timer_eta_epoch.setStyleSheet(timer_style)
    view._timer_eta_total = QLabel("—")
    view._timer_eta_total.setStyleSheet(timer_style)
    timer_grid.addWidget(QLabel("С старта обучения:"), 0, 0)
    timer_grid.addWidget(view._timer_elapsed_total, 0, 1)
    timer_grid.addWidget(QLabel("С начала эпохи:"), 1, 0)
    timer_grid.addWidget(view._timer_elapsed_epoch, 1, 1)
    timer_grid.addWidget(QLabel("Осталось до конца эпохи:"), 2, 0)
    timer_grid.addWidget(view._timer_eta_epoch, 2, 1)
    timer_grid.addWidget(QLabel("Осталось до конца обучения:"), 3, 0)
    timer_grid.addWidget(view._timer_eta_total, 3, 1)
    for r in range(4):
        lbl = timer_grid.itemAtPosition(r, 0).widget()
        if isinstance(lbl, QLabel):
            lbl.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px;")
    metrics_ly.addLayout(timer_grid)
    main_layout.addWidget(metrics_card)

    # Live metrics dashboard (PyQtGraph) — отступы по горизонтали
    metrics_wrap = QWidget()
    metrics_wrap_layout = QHBoxLayout(metrics_wrap)
    metrics_wrap_layout.setContentsMargins(t.space_xl, 0, t.space_xl, 0)
    metrics_wrap_layout.setSpacing(0)
    view._metrics_dashboard = MetricsDashboardWidget(view)
    metrics_wrap_layout.addWidget(view._metrics_dashboard)
    main_layout.addWidget(metrics_wrap)

    # Log (replaces console)
    main_layout.addWidget(QLabel("Лог обучения:"))
    view._log_view = LogView(view)
    view._log_view.setMinimumHeight(200)
    main_layout.addWidget(view._log_view)

    main_layout.addStretch()
    scroll.setWidget(content)
    layout.addWidget(scroll)

    view._on_model_changed(view._model_combo.currentText())
    view._start_metrics_timer()
