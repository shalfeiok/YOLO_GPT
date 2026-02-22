from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import DEFAULT_CONFIDENCE, DEFAULT_IOU_THRESH
from app.features.detection_visualization import list_backends
from app.ui.components.buttons import PrimaryButton, SecondaryButton
from app.ui.theme.tokens import Tokens

RowLabelFn = Callable[[str], QLabel]


def build_model_row(view: object, t: Tokens, layout: QVBoxLayout, row_label: RowLabelFn) -> None:
    """Model picker row (weights path + browse). Mutates view by setting created widgets."""
    # Модель — одна строка: подпись + поле + кнопка
    model_layout = QHBoxLayout()
    model_layout.addWidget(row_label("Модель (.pt):"))
    view._weights_edit = QLineEdit()
    view._weights_edit.setPlaceholderText("Путь к весам .pt или .onnx")
    view._weights_edit.setToolTip(
        "Путь к файлу весов YOLO (.pt) или модели ONNX (.onnx). Для ONNX движка .pt экспортируется в .onnx при первом запуске."
    )
    view._weights_edit.setStyleSheet(
        f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 6px;"
    )
    model_layout.addWidget(view._weights_edit, 1)
    view._browse_weights_btn = SecondaryButton("Обзор…")
    view._browse_weights_btn.setToolTip("Выбрать файл весов (.pt)")
    view._browse_weights_btn.setObjectName("detection_browse_weights")
    view._browse_weights_btn.setMinimumWidth(100)
    view._browse_weights_btn.clicked.connect(view._browse_weights)
    model_layout.addWidget(view._browse_weights_btn)
    layout.addLayout(model_layout)


def build_source_row(view: object, t: Tokens, layout: QVBoxLayout, row_label: RowLabelFn) -> None:
    """Source combo row (screen/window/camera/video) + refresh windows."""
    # Источник — одна строка: подпись + комбо + Обновить окна
    src_layout = QHBoxLayout()
    src_layout.addWidget(row_label("Источник:"))
    view._source_combo = QComboBox()
    view._source_combo.setMinimumHeight(32)
    view._source_combo.setToolTip(
        "Источник видеопотока: экран, окно приложения, веб-камера или видеофайл."
    )
    view._source_combo.setStyleSheet(
        f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 4px;"
    )
    view._source_combo.currentTextChanged.connect(view._on_source_changed)
    src_layout.addWidget(view._source_combo, 1)
    view._refresh_windows_btn = SecondaryButton("Обновить окна")
    view._refresh_windows_btn.setToolTip("Обновить список окон для захвата")
    view._refresh_windows_btn.clicked.connect(view._refresh_windows)
    src_layout.addWidget(view._refresh_windows_btn)
    layout.addLayout(src_layout)


def build_video_row(view: object, t: Tokens, layout: QVBoxLayout, row_label: RowLabelFn) -> None:
    """Video file row (path + browse)."""
    # Видеофайл — одна строка: подпись + поле + кнопка «Обзор…» (как в старом UI)
    video_layout = QHBoxLayout()
    video_layout.addWidget(row_label("Видео (.mp4 и др.):"))
    view._video_edit = QLineEdit()
    view._video_edit.setPlaceholderText("Путь к видео или нажмите «Обзор…»")
    view._video_edit.setToolTip(
        "Путь к видеофайлу (.mp4 и др.). Используется при выборе источника «Видеофайл»."
    )
    view._video_edit.setStyleSheet(
        f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 6px;"
    )
    video_layout.addWidget(view._video_edit, 1)
    view._browse_video_btn = SecondaryButton("Обзор…")
    view._browse_video_btn.setObjectName("detection_browse_video")
    view._browse_video_btn.setMinimumWidth(100)
    view._browse_video_btn.setToolTip("Выбрать видеофайл (для источника «Видеофайл»)")
    view._browse_video_btn.clicked.connect(view._browse_video)
    video_layout.addWidget(view._browse_video_btn)
    layout.addLayout(video_layout)


def build_thresholds_row(
    view: object, t: Tokens, layout: QVBoxLayout, row_label: RowLabelFn
) -> None:
    """Confidence/IoU row and Output settings button."""
    # Confidence / IOU — слева; справа кнопка «Настройки вывода»
    conf_layout = QHBoxLayout()
    conf_layout.addWidget(row_label("Confidence:"))
    view._conf_edit = QLineEdit()
    view._conf_edit.setText(str(DEFAULT_CONFIDENCE))
    view._conf_edit.setFixedWidth(70)
    view._conf_edit.setToolTip(
        "Порог уверенности детекции (0–1). Выше — меньше срабатываний, но меньше ложных."
    )
    view._conf_edit.setStyleSheet(
        f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 6px;"
    )
    conf_layout.addWidget(view._conf_edit)
    conf_layout.addWidget(row_label("IOU:", 50))
    view._iou_edit = QLineEdit()
    view._iou_edit.setText(str(DEFAULT_IOU_THRESH))
    view._iou_edit.setFixedWidth(70)
    view._iou_edit.setToolTip(
        "Порог IoU для NMS (0–1). Пересечение боксов выше этого порога объединяется."
    )
    view._iou_edit.setStyleSheet(
        f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 6px;"
    )
    conf_layout.addWidget(view._iou_edit)
    conf_layout.addStretch()
    view._output_settings_btn = SecondaryButton("Настройки вывода…")
    view._output_settings_btn.setObjectName("detection_output_settings")
    view._output_settings_btn.setToolTip("Путь сохранения результатов детекции и опции вывода")
    view._output_settings_btn.clicked.connect(view._open_output_settings)
    conf_layout.addWidget(view._output_settings_btn)
    layout.addLayout(conf_layout)


def build_render_row(view: object, t: Tokens, layout: QVBoxLayout, row_label: RowLabelFn) -> None:
    """Visualization backend selector row."""
    # Отрисовка — одна строка: подпись + комбо + Настройки + Сбросить
    vis_layout = QHBoxLayout()
    vis_layout.addWidget(row_label("Отрисовка:"))
    view._vis_combo = QComboBox()
    view._vis_combo.addItems([name for _, name in list_backends()])
    view._vis_combo.setMinimumHeight(32)
    view._vis_combo.setToolTip("Бэкенд отрисовки боксов и меток (OpenCV, D3D и др.).")
    view._vis_combo.setStyleSheet(
        f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 4px;"
    )
    view._vis_combo.currentTextChanged.connect(view._on_vis_backend_changed)
    view._sync_vis_combo()
    vis_layout.addWidget(view._vis_combo, 1)
    view._vis_settings_btn = SecondaryButton("Настройки…")
    view._vis_settings_btn.setToolTip("Настройки отрисовки: размер превью, пресеты, цвет меток.")
    view._vis_settings_btn.clicked.connect(view._open_vis_settings)
    vis_layout.addWidget(view._vis_settings_btn)
    view._vis_reset_btn = SecondaryButton("Сбросить")
    view._vis_reset_btn.setToolTip("Сбросить настройки отрисовки к умолчанию.")
    view._vis_reset_btn.clicked.connect(view._reset_vis_default)
    vis_layout.addWidget(view._vis_reset_btn)
    layout.addLayout(vis_layout)


def build_realtime_features(view: object, t: Tokens, layout: QVBoxLayout) -> None:
    """Realtime features group box (solutions toggles + region/FPS/colormap controls)."""
    # Фичи в реальном времени + настройки (region, FPS, colormap)
    view._live_group = QGroupBox("Фичи в реальном времени")
    view._live_group.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    live_layout = QVBoxLayout(view._live_group)
    live_inner = QWidget()
    grid = QGridLayout(live_inner)
    view._live_vars: dict[str, QCheckBox] = {}
    for i, (sol_id, label) in enumerate(
        [
            ("DistanceCalculation", "Distance"),
            ("Heatmap", "Heatmap"),
            ("ObjectCounter", "ObjectCounter"),
            ("RegionCounter", "RegionCounter"),
            ("SpeedEstimator", "Speed"),
            ("TrackZone", "TrackZone"),
        ]
    ):
        cb = QCheckBox(label)
        view._live_vars[sol_id] = cb
        grid.addWidget(cb, i // 4, i % 4)
    live_layout.addWidget(live_inner)
    live_btn_row = QHBoxLayout()
    view._live_settings_btn = SecondaryButton("Настройки фич (region, FPS, colormap)…")
    view._live_settings_btn.clicked.connect(view._open_live_solutions_settings)
    live_btn_row.addWidget(view._live_settings_btn)
    live_btn_row.addStretch()
    live_layout.addLayout(live_btn_row)
    layout.addWidget(view._live_group)


def build_buttons_fps_row(view: object, t: Tokens, layout: QVBoxLayout) -> None:
    """Start/Stop + FPS label row."""
    # Buttons + FPS
    btn_layout = QHBoxLayout()
    view._start_btn = PrimaryButton("Старт детекции")
    view._start_btn.setToolTip("Запустить детекцию по выбранной модели и источнику.")
    view._start_btn.setToolTip("Запустить детекцию в реальном времени по выбранному источнику")
    view._start_btn.clicked.connect(view._start_detection)
    view._stop_btn = SecondaryButton("Стоп")
    view._stop_btn.setToolTip("Остановить детекцию.")
    view._stop_btn.setToolTip("Остановить детекцию")
    view._stop_btn.setEnabled(False)
    view._stop_btn.clicked.connect(view._stop_detection)
    view._fps_label = QLabel("FPS: —")
    view._fps_label.setStyleSheet(f"font-weight: bold; color: {t.text_primary};")
    btn_layout.addWidget(view._start_btn)
    btn_layout.addWidget(view._stop_btn)
    btn_layout.addWidget(view._fps_label)
    layout.addLayout(btn_layout)
    view._detection_status_label = QLabel(
        "Загрузите модель и нажмите «Старт». Превью откроется в отдельном окне «YOLO Detection»."
    )
    view._detection_status_label.setStyleSheet(
        f"color: {t.text_secondary}; font-size: 12px; padding: 4px 0;"
    )
    layout.addWidget(view._detection_status_label)
    layout.addStretch()
