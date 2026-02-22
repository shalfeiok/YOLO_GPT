"""
Detection View: model, source (screen/window/camera/video), confidence/IOU,
visualization backend, Start/Stop, FPS. Preview in separate OpenCV window (unchanged logic).
"""

from __future__ import annotations

import contextlib
import io
import logging
import time
import uuid
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Lock, Thread
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from app.config import PREVIEW_MAX_SIZE
from app.features.detection_visualization import (
    get_backend,
    list_backends,
    load_visualization_config,
    reset_visualization_config_to_default,
    save_visualization_config,
)
from app.features.detection_visualization.domain import (
    BACKEND_D3DSHOT_PYTORCH,
    VISUALIZATION_BACKEND_DISPLAY_NAMES,
    builtin_visualization_presets,
    get_config_section,
    use_gpu_tensor_for_preview,
)
from app.features.detection_visualization.frame_buffers import FrameSlot, PreviewBuffer
from app.features.detection_visualization.repository import (
    delete_user_preset,
    get_user_presets,
    save_user_preset,
)
from app.features.integrations_config import load_config, save_config
from app.ui.components.buttons import PrimaryButton, SecondaryButton
from app.ui.components.inputs import NoWheelSpinBox
from app.ui.theme.tokens import Tokens

from .sections import (
    build_buttons_fps_row,
    build_model_row,
    build_realtime_features,
    build_render_row,
    build_source_row,
    build_thresholds_row,
    build_video_row,
)

if TYPE_CHECKING:
    from app.ui.infrastructure.di import Container

from app.application.facades.capture import FrameSource
from app.application.use_cases.start_detection import StartDetectionError, StartDetectionRequest
from app.application.use_cases.stop_detection import StopDetectionRequest
from app.core.events.job_events import JobCancelled, JobLogLine, JobProgress, JobStarted
from app.core.observability.run_manifest import register_run

log = logging.getLogger(__name__)

CV2_WIN_NAME = "YOLO Detection"

CAPTURE_INTERVAL_MS = 25
FRAME_QUEUE_GET_TIMEOUT_S = 0.03
FPS_TICK_MS = 120
LABEL_WIDTH = 140  # ширина подписей для выравнивания полей по горизонтали


class DetectionMetrics:
    """
    Part 7.11: Atomic, thread-safe metrics; single lock, no allocation in set_* (hot path).
    get_metrics() allocates dict only when called (UI thread); set_* only write floats.
    """

    __slots__ = ("_capture_ms", "_inference_ms", "_render_ms", "_lock")

    def __init__(self) -> None:
        self._capture_ms: float = 0.0
        self._inference_ms: float = 0.0
        self._render_ms: float = 0.0
        self._lock = Lock()

    def set_capture_ms(self, ms: float) -> None:
        with self._lock:
            self._capture_ms = ms

    def set_inference_ms(self, ms: float) -> None:
        with self._lock:
            self._inference_ms = ms

    def set_render_ms(self, ms: float) -> None:
        with self._lock:
            self._render_ms = ms

    def get_metrics(self) -> dict[str, float]:
        with self._lock:
            return {
                "capture_ms": self._capture_ms,
                "inference_ms": self._inference_ms,
                "render_ms": self._render_ms,
            }


def _row_label(text: str, width: int = LABEL_WIDTH) -> QLabel:
    lbl = QLabel(text)
    lbl.setMinimumWidth(width)
    return lbl


class DetectionView(QWidget):
    """Detection tab: weights, source, conf/IOU, visualization, Start/Stop, FPS. Same pipeline as CTk tab."""

    stop_cleanup_done = Signal(int)

    def __init__(self, container: Container) -> None:
        super().__init__()
        self._container = container
        self._detection = container.detection
        self._capture = container.window_capture
        # Part 4.5: Event for deterministic thread lifecycle (clear = stop, set = run)
        self._run_event: Event = Event()
        self._capture_thread: Thread | None = None
        self._screen_capture_thread: Thread | None = None
        self._inference_thread: Thread | None = None
        self._onnx_export_poll_timer: QTimer | None = None
        self._pending_onnx: tuple | None = None
        self._current_hwnd: int | None = None
        self._use_full_screen = False
        self._opencv_source: FrameSource | None = None
        self._window_list: list[tuple[int, str]] = []
        # Low-overhead frame slot: drop-old-frame, no Queue overhead (Part 1.2)
        self._frame_slot: FrameSlot = FrameSlot()
        self._fps_queue: Queue = Queue(maxsize=4)
        # Double-buffer preview: no numpy.copy(), producer/consumer use different slots (Part 1.1)
        self._preview_buffer: PreviewBuffer = PreviewBuffer()
        self._run_id = 0
        self._detection_job_id: str | None = None
        self._visualization_backend = None
        self._active_detector = None  # устанавливается при Старт: detector или detector_onnx
        self._metrics = DetectionMetrics()
        self._capture_timer = QTimer(self)
        self._capture_timer.timeout.connect(self._schedule_capture_frame)
        self._fps_timer = QTimer(self)
        self._fps_timer.timeout.connect(self._tick_fps)
        self.stop_cleanup_done.connect(self._finalize_stop_ui)
        self._build_ui()
        QTimer.singleShot(0, self._refresh_windows)

    def _build_ui(self) -> None:
        t = Tokens
        old_layout = self.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
        layout = old_layout if isinstance(old_layout, QVBoxLayout) else QVBoxLayout(self)
        layout.setSpacing(t.space_lg)
        layout.setContentsMargins(t.space_lg, t.space_lg, t.space_lg, t.space_lg)

        build_model_row(self, t, layout, _row_label)
        build_source_row(self, t, layout, _row_label)
        build_video_row(self, t, layout, _row_label)
        build_thresholds_row(self, t, layout, _row_label)
        build_render_row(self, t, layout, _row_label)
        build_realtime_features(self, t, layout)
        build_buttons_fps_row(self, t, layout)

    def refresh_theme(self) -> None:
        """Re-apply theme-dependent styles (called when theme changes)."""
        t = Tokens
        self._weights_edit.setStyleSheet(
            f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 6px;"
        )
        self._source_combo.setStyleSheet(
            f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 4px;"
        )
        self._video_edit.setStyleSheet(
            f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 6px;"
        )
        self._conf_edit.setStyleSheet(
            f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 6px;"
        )
        self._iou_edit.setStyleSheet(
            f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 6px;"
        )
        self._vis_combo.setStyleSheet(
            f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 4px;"
        )
        self._fps_label.setStyleSheet(f"font-weight: bold; color: {t.text_primary};")
        self._live_group.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}"
        )

    def _get_vis_backend_id(self) -> str:
        name = self._vis_combo.currentText()
        for bid, dname in list_backends():
            if dname == name:
                return bid
        return "opencv"

    def _sync_vis_combo(self) -> None:
        cfg = load_visualization_config()
        bid = cfg.get("backend_id", "opencv")
        self._vis_combo.setCurrentText(
            VISUALIZATION_BACKEND_DISPLAY_NAMES.get(bid, "OpenCV (GDI/mss + imshow)")
        )

    def _on_vis_backend_changed(self, _: str) -> None:
        bid = self._get_vis_backend_id()
        cfg = load_visualization_config()
        cfg["backend_id"] = bid
        save_visualization_config(cfg)

    def _open_vis_settings(self) -> None:
        """Диалог настроек визуализации: профили, бэкенд, превью, настройки фич (region, FPS, colormap)."""
        from app.features.ultralytics_solutions.domain import SolutionsConfig
        from app.features.ultralytics_solutions.repository import (
            load_solutions_config,
            save_solutions_config,
        )

        t = Tokens
        cfg = load_visualization_config()
        bid = cfg.get("backend_id", BACKEND_D3DSHOT_PYTORCH)
        solutions_cfg = load_solutions_config()

        dlg = QDialog(self)
        dlg.setWindowTitle("Настройки визуализации детекции")
        dlg.setMinimumWidth(460)
        dlg.setMinimumHeight(520)
        main_layout = QVBoxLayout(dlg)
        style_edit = f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 6px;"

        # Профиль
        grp_profile = QGroupBox("Профиль")
        grp_profile.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
        profile_ly = QHBoxLayout(grp_profile)
        profile_ly.addWidget(QLabel("Профиль:"))
        combo_profile = QComboBox()
        combo_profile.setStyleSheet(style_edit)
        combo_profile.setToolTip("Выберите сохранённый профиль или «Стандартный».")

        def _fill_profile_combo() -> None:
            combo_profile.blockSignals(True)
            combo_profile.clear()
            combo_profile.addItem("Стандартный", None)
            for p in get_user_presets():
                combo_profile.addItem(p.get("name", ""), p.get("config"))
            combo_profile.blockSignals(False)

        _fill_profile_combo()
        profile_ly.addWidget(combo_profile, 1)
        btn_std_profile = SecondaryButton("Стандартный")
        btn_std_profile.setToolTip("Сбросить к значениям по умолчанию")
        profile_ly.addWidget(btn_std_profile)
        btn_save_profile = SecondaryButton("Сохранить как…")
        btn_save_profile.setToolTip("Сохранить текущие настройки как новый профиль")
        profile_ly.addWidget(btn_save_profile)
        main_layout.addWidget(grp_profile)

        # Бэкенд (можно менять в диалоге или через пресет)
        row_backend = QHBoxLayout()
        row_backend.addWidget(QLabel("Бэкенд отрисовки:"))
        combo_backend = QComboBox()
        for backend_id, display_name in list_backends():
            combo_backend.addItem(display_name, backend_id)
        combo_backend.setStyleSheet(style_edit)
        idx_b = combo_backend.findData(bid)
        if idx_b >= 0:
            combo_backend.setCurrentIndex(idx_b)
        row_backend.addWidget(combo_backend, 1)
        main_layout.addLayout(row_backend)

        # Настройки бэкенда
        grp_settings = QGroupBox("Настройки бэкенда")
        grp_settings.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
        form = QFormLayout(grp_settings)

        def _preview_w(b: str) -> int:
            return cfg.get(get_config_section(b), {}).get("preview_max_w", 0)

        def _preview_h(b: str) -> int:
            return cfg.get(get_config_section(b), {}).get("preview_max_h", 0)

        spin_w = NoWheelSpinBox()
        spin_w.setRange(0, 7680)
        spin_w.setValue(_preview_w(bid))
        spin_w.setSpecialValueText("без ресайза")
        spin_w.setStyleSheet(style_edit)
        form.addRow("Макс. ширина превью (0 = как в источнике):", spin_w)

        spin_h = NoWheelSpinBox()
        spin_h.setRange(0, 4320)
        spin_h.setValue(_preview_h(bid))
        spin_h.setSpecialValueText("без ресайза")
        spin_h.setStyleSheet(style_edit)
        form.addRow("Макс. высота превью (0 = как в источнике):", spin_h)

        cb_cuda = QCheckBox("Использовать CUDA для ресайза (OpenCV / ONNX)")
        cb_cuda.setChecked(cfg.get(get_config_section(bid), {}).get("use_cuda_resize", True))
        form.addRow("", cb_cuda)

        cb_d3d = QCheckBox("Использовать D3DShot для захвата экрана")
        cb_d3d.setChecked(cfg.get("d3dshot_pytorch", {}).get("use_d3dshot_capture", True))
        form.addRow("", cb_d3d)
        main_layout.addWidget(grp_settings)

        # Настройки фич (Solutions: region, FPS, colormap)
        grp_solutions = QGroupBox("Настройки фич (region, FPS, colormap)")
        grp_solutions.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
        form_sol = QFormLayout(grp_solutions)
        region_edit = QLineEdit()
        region_edit.setText(solutions_cfg.region_points or "[(20, 400), (1260, 400)]")
        region_edit.setStyleSheet(style_edit)
        region_edit.setPlaceholderText("[(x1,y1), (x2,y2), ...]")
        form_sol.addRow("region (линия/полигон):", region_edit)
        fps_spin = NoWheelSpinBox()
        fps_spin.setRange(1, 120)
        fps_spin.setValue(int(solutions_cfg.fps) if solutions_cfg.fps else 30)
        fps_spin.setStyleSheet(style_edit)
        form_sol.addRow("FPS (SpeedEstimator):", fps_spin)
        colormap_combo = QComboBox()
        colormap_combo.addItems(
            [
                "COLORMAP_AUTUMN",
                "COLORMAP_BONE",
                "COLORMAP_JET",
                "COLORMAP_WINTER",
                "COLORMAP_RAINBOW",
                "COLORMAP_OCEAN",
                "COLORMAP_SUMMER",
                "COLORMAP_SPRING",
                "COLORMAP_COOL",
                "COLORMAP_HSV",
                "COLORMAP_PINK",
                "COLORMAP_HOT",
            ]
        )
        cm = (solutions_cfg.colormap or "COLORMAP_JET").replace("cv2.", "").strip()
        idx_cm = colormap_combo.findText(cm)
        if idx_cm >= 0:
            colormap_combo.setCurrentIndex(idx_cm)
        colormap_combo.setStyleSheet(style_edit)
        form_sol.addRow("Colormap (Heatmap):", colormap_combo)
        main_layout.addWidget(grp_solutions)

        # Пресеты
        grp_presets = QGroupBox("Пресеты")
        grp_presets.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
        presets_layout = QVBoxLayout(grp_presets)

        row_builtin = QHBoxLayout()
        row_builtin.addWidget(QLabel("Встроенные:"))
        combo_builtin = QComboBox()
        for name, _ in builtin_visualization_presets():
            combo_builtin.addItem(name)
        combo_builtin.setStyleSheet(style_edit)
        row_builtin.addWidget(combo_builtin, 1)
        btn_apply_builtin = SecondaryButton("Применить")
        row_builtin.addWidget(btn_apply_builtin)
        presets_layout.addLayout(row_builtin)

        row_user = QHBoxLayout()
        row_user.addWidget(QLabel("Сохранённые:"))
        combo_user = QComboBox()

        def _fill_user_presets() -> None:
            combo_user.clear()
            for p in get_user_presets():
                combo_user.addItem(p.get("name", ""), p.get("config"))

        _fill_user_presets()
        combo_user.setStyleSheet(style_edit)
        row_user.addWidget(combo_user, 1)
        btn_apply_user = SecondaryButton("Применить")
        btn_del_user = SecondaryButton("Удалить")
        row_user.addWidget(btn_apply_user)
        row_user.addWidget(btn_del_user)
        presets_layout.addLayout(row_user)

        row_save = QHBoxLayout()
        row_save.addWidget(QLabel("Сохранить текущие как:"))
        le_preset_name = QLineEdit()
        le_preset_name.setPlaceholderText("Имя пресета")
        le_preset_name.setStyleSheet(style_edit)
        row_save.addWidget(le_preset_name, 1)
        btn_save_preset = SecondaryButton("Сохранить пресет")
        row_save.addWidget(btn_save_preset)
        presets_layout.addLayout(row_save)
        main_layout.addWidget(grp_presets)

        def _config_from_form() -> dict:
            c = load_visualization_config()
            c["backend_id"] = combo_backend.currentData() or bid
            c["opencv"] = {
                "preview_max_w": spin_w.value(),
                "preview_max_h": spin_h.value(),
                "use_cuda_resize": cb_cuda.isChecked(),
            }
            c["d3dshot_pytorch"] = {
                "preview_max_w": spin_w.value(),
                "preview_max_h": spin_h.value(),
                "use_d3dshot_capture": cb_d3d.isChecked(),
            }
            c["onnx"] = {
                "preview_max_w": spin_w.value(),
                "preview_max_h": spin_h.value(),
                "use_cuda_resize": cb_cuda.isChecked(),
            }
            c["solutions"] = {
                "region_points": region_edit.text().strip() or "[(20, 400), (1260, 400)]",
                "fps": float(fps_spin.value()),
                "colormap": colormap_combo.currentText(),
            }
            if "presets" not in c:
                c["presets"] = []
            return c

        def _apply_preset_config(preset_cfg: dict) -> None:
            preset_cfg = dict(preset_cfg)
            bid_p = preset_cfg.get("backend_id", bid)
            section = get_config_section(bid_p)
            sec_cfg = preset_cfg.get(section, {})
            idx_p = combo_backend.findData(bid_p)
            if idx_p >= 0:
                combo_backend.setCurrentIndex(idx_p)
            spin_w.setValue(sec_cfg.get("preview_max_w", 0))
            spin_h.setValue(sec_cfg.get("preview_max_h", 0))
            cb_cuda.setChecked(sec_cfg.get("use_cuda_resize", True))
            cb_d3d.setChecked(sec_cfg.get("use_d3dshot_capture", True))
            sol = preset_cfg.get("solutions")
            if sol:
                region_edit.setText(sol.get("region_points", "[(20, 400), (1260, 400)]"))
                fps_spin.setValue(int(sol.get("fps", 30)))
                cm = (sol.get("colormap") or "COLORMAP_JET").replace("cv2.", "").strip()
                idx_cm = colormap_combo.findText(cm)
                if idx_cm >= 0:
                    colormap_combo.setCurrentIndex(idx_cm)

        def _on_profile_changed() -> None:
            idx = combo_profile.currentIndex()
            if idx <= 0:
                return
            cfg_u = combo_profile.currentData()
            if isinstance(cfg_u, dict):
                _apply_preset_config(cfg_u)

        def _on_std_profile() -> None:
            from app.features.detection_visualization.domain import default_visualization_config

            combo_profile.blockSignals(True)
            combo_profile.setCurrentIndex(0)
            combo_profile.blockSignals(False)
            _apply_preset_config(default_visualization_config())
            region_edit.setText("[(20, 400), (1260, 400)]")
            fps_spin.setValue(30)
            idx_cm = colormap_combo.findText("COLORMAP_JET")
            if idx_cm >= 0:
                colormap_combo.setCurrentIndex(idx_cm)

        def _on_save_profile_as() -> None:
            name, ok = QInputDialog.getText(dlg, "Сохранить профиль", "Имя профиля:")
            if not ok or not name or not name.strip():
                return
            name = name.strip()
            save_user_preset(name, _config_from_form())
            _fill_profile_combo()
            idx = combo_profile.findText(name)
            if idx >= 0:
                combo_profile.setCurrentIndex(idx)
            QMessageBox.information(dlg, "Профиль", f"Профиль «{name}» сохранён.")

        combo_profile.currentIndexChanged.connect(_on_profile_changed)
        btn_std_profile.clicked.connect(_on_std_profile)
        btn_save_profile.clicked.connect(_on_save_profile_as)

        def _on_apply_builtin() -> None:
            presets = builtin_visualization_presets()
            idx = combo_builtin.currentIndex()
            if 0 <= idx < len(presets):
                _apply_preset_config(presets[idx][1])

        def _on_apply_user() -> None:
            if combo_user.currentIndex() < 0:
                return
            cfg_u = combo_user.currentData()
            if isinstance(cfg_u, dict):
                _apply_preset_config(cfg_u)

        def _on_save_preset() -> None:
            name = le_preset_name.text().strip()
            if not name:
                QMessageBox.warning(dlg, "Имя", "Введите имя пресета.")
                return
            save_user_preset(name, _config_from_form())
            _fill_user_presets()
            le_preset_name.clear()
            QMessageBox.information(dlg, "Сохранено", f"Пресет «{name}» сохранён.")

        def _on_del_preset() -> None:
            if combo_user.currentIndex() < 0:
                return
            name = combo_user.currentText()
            if not name:
                return
            delete_user_preset(name)
            _fill_user_presets()
            QMessageBox.information(dlg, "Удалено", f"Пресет «{name}» удалён.")

        btn_apply_builtin.clicked.connect(_on_apply_builtin)
        btn_apply_user.clicked.connect(_on_apply_user)
        btn_save_preset.clicked.connect(_on_save_preset)
        btn_del_user.clicked.connect(_on_del_preset)

        # Кнопки Сохранить / Отмена
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = PrimaryButton("Сохранить")
        cancel_btn = SecondaryButton("Отмена")

        def _do_save() -> None:
            c = _config_from_form()
            save_visualization_config(c)
            self._sync_vis_combo()
            saved_bid = c.get("backend_id", bid)
            backend = get_backend(saved_bid)
            if backend:
                section = get_config_section(saved_bid)
                backend.apply_settings(c.get(section, {}))
            sol = c.get("solutions", {})
            existing = load_solutions_config()
            sol_cfg = SolutionsConfig(
                solution_type=existing.solution_type,
                model_path=existing.model_path,
                source=existing.source,
                output_path=existing.output_path,
                region_points=sol.get("region_points", "[(20, 400), (1260, 400)]"),
                fps=float(sol.get("fps", 30)),
                colormap=sol.get("colormap", "COLORMAP_JET"),
            )
            save_solutions_config(sol_cfg)
            QMessageBox.information(dlg, "Сохранено", "Настройки визуализации и фич сохранены.")
            dlg.accept()

        save_btn.clicked.connect(_do_save)
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        main_layout.addLayout(btn_row)

        dlg.exec()

    def _reset_vis_default(self) -> None:
        reset_visualization_config_to_default()
        self._sync_vis_combo()
        QMessageBox.information(self, "Визуализация", "Настройки отрисовки сброшены к стандарту.")

    def _open_live_solutions_settings(self) -> None:
        """Диалог настроек фич в реальном времени: region_points, FPS, colormap."""
        from app.features.ultralytics_solutions.repository import (
            load_solutions_config,
            save_solutions_config,
        )

        t = Tokens
        cfg = load_solutions_config()
        dlg = QDialog(self)
        dlg.setWindowTitle("Настройки фич (Solutions)")
        form = QFormLayout(dlg)
        style = f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 6px;"
        region_edit = QLineEdit()
        region_edit.setText(cfg.region_points or "[(20, 400), (1260, 400)]")
        region_edit.setStyleSheet(style)
        form.addRow("region (линия/полигон):", region_edit)
        fps_spin = NoWheelSpinBox()
        fps_spin.setRange(1, 120)
        fps_spin.setValue(int(cfg.fps) if cfg.fps else 30)
        fps_spin.setStyleSheet(style)
        form.addRow("FPS (SpeedEstimator):", fps_spin)
        colormap_combo = QComboBox()
        colormap_combo.addItems(
            [
                "COLORMAP_AUTUMN",
                "COLORMAP_BONE",
                "COLORMAP_JET",
                "COLORMAP_WINTER",
                "COLORMAP_RAINBOW",
                "COLORMAP_OCEAN",
                "COLORMAP_SUMMER",
                "COLORMAP_SPRING",
                "COLORMAP_COOL",
                "COLORMAP_HSV",
                "COLORMAP_PINK",
                "COLORMAP_HOT",
            ]
        )
        cm = (cfg.colormap or "COLORMAP_JET").replace("cv2.", "").strip()
        idx = colormap_combo.findText(cm)
        if idx >= 0:
            colormap_combo.setCurrentIndex(idx)
        colormap_combo.setStyleSheet(style)
        form.addRow("Colormap (Heatmap):", colormap_combo)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = PrimaryButton("Сохранить")
        cancel_btn = SecondaryButton("Отмена")

        def _save() -> None:
            cfg.region_points = region_edit.text().strip() or "[(20, 400), (1260, 400)]"
            cfg.fps = float(fps_spin.value())
            cfg.colormap = colormap_combo.currentText()
            save_solutions_config(cfg)
            QMessageBox.information(dlg, "Сохранено", "Настройки фич сохранены.")
            dlg.accept()

        save_btn.clicked.connect(_save)
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        form.addRow(btn_row)
        dlg.exec()

    def _browse_weights(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Веса модели",
            self._weights_edit.text() or ".",
            "PyTorch / ONNX (*.pt *.onnx);;PyTorch (*.pt);;ONNX (*.onnx);;Все файлы (*.*)",
        )
        if path:
            self._weights_edit.setText(path)

    def _browse_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Видеофайл",
            self._video_edit.text() or ".",
            "MP4 (*.mp4);;AVI (*.avi);;Все файлы (*.*)",
        )
        if path:
            self._video_edit.setText(path)

    def _open_output_settings(self) -> None:
        """Диалог «Настройки вывода»: путь сохранения, опция сохранения кадров, кнопка Сохранить."""
        cfg = load_config().get("detection_output", {"save_path": "", "save_frames": False})
        dlg = QDialog(self)
        dlg.setWindowTitle("Настройки вывода")
        t = Tokens
        form = QFormLayout(dlg)
        path_edit = QLineEdit()
        path_edit.setText(cfg.get("save_path", "") or "")
        path_edit.setPlaceholderText("Папка для сохранения кадров/видео")
        path_edit.setStyleSheet(
            f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 6px;"
        )
        path_edit.setMinimumWidth(320)
        browse_btn = SecondaryButton("Обзор…")
        browse_btn.setMinimumWidth(100)

        def choose_dir() -> None:
            folder = QFileDialog.getExistingDirectory(
                dlg, "Папка сохранения", path_edit.text() or "."
            )
            if folder:
                path_edit.setText(folder)

        browse_btn.clicked.connect(choose_dir)
        path_row = QHBoxLayout()
        path_row.addWidget(path_edit, 1)
        path_row.addWidget(browse_btn)
        form.addRow("Папка сохранения:", path_row)
        save_frames_cb = QCheckBox("Сохранять кадры при детекции")
        save_frames_cb.setChecked(bool(cfg.get("save_frames", False)))
        form.addRow("", save_frames_cb)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = PrimaryButton("Сохранить")
        cancel_btn = SecondaryButton("Отмена")

        def do_save() -> None:
            config = load_config()
            config.setdefault("detection_output", {"save_path": "", "save_frames": False})
            config["detection_output"]["save_path"] = path_edit.text().strip()
            config["detection_output"]["save_frames"] = save_frames_cb.isChecked()
            save_config(config)
            QMessageBox.information(dlg, "Сохранено", "Настройки вывода сохранены.")
            dlg.accept()

        save_btn.clicked.connect(do_save)
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        form.addRow(btn_row)
        dlg.exec()

    def _refresh_windows(self) -> None:
        current = self._source_combo.currentText().strip()
        try:
            self._window_list = self._capture.list_windows()
        except Exception:
            self._window_list = []
        titles = ["Весь экран"] + [t for _, t in self._window_list] + ["Камера", "Видеофайл"]
        self._source_combo.clear()
        self._source_combo.addItems(titles)
        if current:
            idx = self._source_combo.findText(current)
            if idx >= 0:
                self._source_combo.setCurrentIndex(idx)

    def _update_window_list_only(self) -> None:
        self._window_list = self._capture.list_windows()

    def _on_source_changed(self, choice: str) -> None:
        self._use_full_screen = choice == "Весь экран"
        self._current_hwnd = None
        if choice in ("Камера", "Видеофайл"):
            return
        for hwnd, title in self._window_list:
            if title == choice:
                self._current_hwnd = hwnd
                return

    def _start_detection(self) -> None:
        path = self._weights_edit.text().strip()
        if not path or not Path(path).exists():
            QMessageBox.critical(self, "Ошибка", "Укажите существующий файл весов (.pt или .onnx).")
            return

        self._run_event.clear()
        if self._opencv_source is not None:
            try:
                self._opencv_source.release()
            except Exception:
                import logging

                logging.getLogger(__name__).debug("Detection view update failed", exc_info=True)
            self._opencv_source = None
        for th in (self._capture_thread, self._screen_capture_thread, self._inference_thread):
            if th is not None and th.is_alive():
                th.join(timeout=2.0)
        self._capture_thread = None
        self._screen_capture_thread = None
        self._inference_thread = None
        self._update_window_list_only()

        source_choice = self._source_combo.currentText()
        if source_choice == "Весь экран":
            self._current_hwnd = None
            self._use_full_screen = True
            self._opencv_source = None
        elif source_choice == "Камера":
            self._current_hwnd = None
            self._use_full_screen = False
            self._opencv_source = self._container.create_frame_source(0)
            if not self._opencv_source.is_opened():
                QMessageBox.critical(self, "Ошибка", "Не удалось открыть камеру (устройство 0).")
                return
        elif source_choice == "Видеофайл":
            video_path = self._video_edit.text().strip()
            if not video_path or not Path(video_path).exists():
                QMessageBox.critical(self, "Ошибка", "Укажите существующий видеофайл.")
                return
            self._current_hwnd = None
            self._use_full_screen = False
            self._opencv_source = self._container.create_frame_source(video_path)
            if not self._opencv_source.is_opened():
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть видео: {video_path}")
                self._opencv_source = None
                return
        else:
            self._opencv_source = None
            self._use_full_screen = False
            self._current_hwnd = None
            for hwnd, title in self._window_list:
                if title == source_choice:
                    self._current_hwnd = hwnd
                    break
            if self._current_hwnd is None:
                QMessageBox.warning(
                    self,
                    "Захват окна",
                    "Выбранное окно не найдено. Нажмите «Обновить окна» и выберите снова.",
                )
                return
            test_frame = self._capture.capture_window(self._current_hwnd)
            if test_frame is None:
                QMessageBox.warning(
                    self,
                    "Захват окна",
                    "Не удалось получить кадр от окна. Разверните окно и нажмите Старт снова.",
                )
                return

        vis_config = load_visualization_config()
        backend_id = vis_config.get("backend_id", "opencv")
        try:
            res = self._container.start_detection_use_case.execute(
                StartDetectionRequest(
                    weights_path=Path(path),
                    confidence_text=self._conf_edit.text(),
                    iou_text=self._iou_edit.text(),
                    backend_id=backend_id,
                )
            )
        except StartDetectionError as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return

        self._active_detector = res.detector
        self._detection_job_id = uuid.uuid4().hex
        self._container.event_bus.publish(
            JobStarted(job_id=self._detection_job_id, name="detection")
        )
        self._container.job_registry.set_cancel(self._detection_job_id, self._stop_detection)
        self._container.event_bus.publish(
            JobProgress(
                job_id=self._detection_job_id, name="detection", progress=0.0, message="started"
            )
        )
        try:
            register_run(
                job_id=self._detection_job_id,
                run_type="detection",
                spec={
                    "weights_path": path,
                    "source": source_choice,
                    "confidence": self._conf_edit.text(),
                    "iou": self._iou_edit.text(),
                    "backend_id": backend_id,
                },
                artifacts={"project_root": str(self._container.project_root)},
            )
        except Exception:
            log.exception("Failed to create detection run manifest")
        conf_f, iou_f = res.confidence, res.iou

        # Part 3.4: ONNX export may be async; poll until loaded then start pipeline (no UI freeze)
        if getattr(self._active_detector, "is_exporting", lambda: False)():
            self._detection_status_label.setText("Экспорт в ONNX… Ожидание завершения.")
            self._start_btn.setEnabled(False)
            self._run_id += 1
            this_run_id = self._run_id
            self._pending_onnx = (this_run_id, conf_f, iou_f, path, backend_id, vis_config)

            def _poll_onnx_ready() -> None:
                if (
                    not getattr(self, "_pending_onnx", None)
                    or self._pending_onnx[0] != self._run_id
                ):
                    return
                err = getattr(self._active_detector, "get_export_error", lambda: None)()
                if err:
                    self._detection_status_label.setText(f"Ошибка экспорта ONNX: {err}")
                    self._start_btn.setEnabled(True)
                    self._pending_onnx = None
                    if self._onnx_export_poll_timer:
                        self._onnx_export_poll_timer.stop()
                        self._onnx_export_poll_timer = None
                    return
                if self._active_detector.is_loaded:
                    if self._onnx_export_poll_timer:
                        self._onnx_export_poll_timer.stop()
                        self._onnx_export_poll_timer = None
                    pending = self._pending_onnx
                    self._pending_onnx = None
                    if pending and pending[0] == self._run_id:
                        self._start_pipeline_after_load(*pending[1:])

            self._onnx_export_poll_timer = QTimer(self)
            self._onnx_export_poll_timer.timeout.connect(_poll_onnx_ready)
            self._onnx_export_poll_timer.start(500)
            return

        self._run_id += 1
        this_run_id = self._run_id
        self._start_pipeline_after_load(conf_f, iou_f, path, backend_id, vis_config)

    def _start_pipeline_after_load(
        self,
        conf_f: float,
        iou_f: float,
        path: str,
        backend_id: str,
        vis_config: dict,
    ) -> None:
        """Part 4.6: Start run event, display backend, and capture/inference threads."""
        this_run_id = self._run_id
        self._run_event.set()
        self._frame_slot.clear()
        self._preview_buffer.clear()
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)

        self._visualization_backend = get_backend(backend_id)
        section = get_config_section(backend_id)
        self._visualization_backend.apply_settings(vis_config.get(section, {}))

        self._detection_status_label.setText(
            f"Превью в окне «{CV2_WIN_NAME}». Нажмите Стоп или Q в окне превью для остановки."
        )
        window_name = CV2_WIN_NAME

        def on_stop_cb() -> None:
            QTimer.singleShot(0, lambda: self._on_detection_stopped(this_run_id))

        def on_render_metrics(ms: float) -> None:
            self._metrics.set_render_ms(ms)

        self._visualization_backend.start_display(
            run_id=this_run_id,
            window_name=window_name,
            preview_queue=self._preview_buffer,
            max_w=PREVIEW_MAX_SIZE[0],
            max_h=PREVIEW_MAX_SIZE[1],
            is_running_getter=lambda: self._run_event.is_set(),
            run_id_getter=lambda: self._run_id,
            on_stop=on_stop_cb,
            on_q_key=lambda: QTimer.singleShot(0, self._stop_detection),
            on_render_metrics=on_render_metrics,
        )
        self._container.event_bus.publish(
            JobProgress(
                job_id=self._detection_job_id, name="detection", progress=0.1, message="running"
            )
        )
        self._fps_timer.start(FPS_TICK_MS)

        enabled_live_ids = [sol_id for sol_id, cb in self._live_vars.items() if cb.isChecked()]
        live_solutions_config: list = []
        if enabled_live_ids:
            try:
                import cv2 as _cv2

                from app.features.integrations_config import load_config

                sol_cfg = load_config().get("ultralytics_solutions", {})
                region_pts = sol_cfg.get("region_points", "[(20, 400), (1260, 400)]")
                try:
                    region = eval(region_pts) if isinstance(region_pts, str) else region_pts
                except Exception:
                    region = [(20, 400), (1260, 400)]
                fps_val = float(sol_cfg.get("fps", 30))
                colormap_name = (
                    (sol_cfg.get("colormap") or "COLORMAP_JET").replace("cv2.", "").strip()
                )
                _sol_display_names = {
                    "DistanceCalculation": "Distance",
                    "Heatmap": "Heatmap",
                    "ObjectCounter": "ObjectCounter",
                    "RegionCounter": "RegionCounter",
                    "SpeedEstimator": "Speed",
                    "TrackZone": "TrackZone",
                }
                for sol_id in enabled_live_ids:
                    live_solutions_config.append((sol_id, _sol_display_names.get(sol_id, sol_id)))
                _sol_region = region
                _sol_fps_val = fps_val
                _sol_colormap_name = colormap_name
                _sol_cv2 = _cv2
            except Exception:
                live_solutions_config = []
                _sol_region = [(20, 400), (1260, 400)]
                _sol_fps_val = 30.0
                _sol_colormap_name = "COLORMAP_JET"
                _sol_cv2 = None
        else:
            _sol_region = [(20, 400), (1260, 400)]
            _sol_fps_val = 30.0
            _sol_colormap_name = "COLORMAP_JET"
            _sol_cv2 = None

        def capture_loop() -> None:
            try:
                while self._run_event.is_set() and self._opencv_source is not None:
                    t0 = time.perf_counter()
                    ret, frame = self._opencv_source.read()
                    self._metrics.set_capture_ms((time.perf_counter() - t0) * 1000.0)
                    if not ret:
                        time.sleep(0.1)
                        continue
                    if frame is not None:
                        self._frame_slot.put_nowait(frame)
                    time.sleep(0.03)
            except Exception:
                log.exception("capture_loop")

        def inference_loop() -> None:
            import numpy as np

            class _LineEmitter(io.TextIOBase):
                def __init__(self) -> None:
                    self._buf = ""

                def write(self, s: str) -> int:
                    self._buf += s
                    while "\n" in self._buf:
                        line, self._buf = self._buf.split("\n", 1)
                        _publish_log_line(line)
                    return len(s)

                def flush(self) -> None:
                    if self._buf:
                        _publish_log_line(self._buf)
                    self._buf = ""

            def _publish_log_line(line: str) -> None:
                clean = str(line).strip()
                if not clean or self._detection_job_id is None:
                    return
                self._container.event_bus.publish(
                    JobLogLine(job_id=self._detection_job_id, name="detection", line=clean)
                )

            live_annotators: list = []

            def _ensure_annotators() -> None:
                if live_annotators or not live_solutions_config:
                    return
                _cv2 = _sol_cv2
                if _cv2 is None:
                    return
                try:
                    import ultralytics.utils.checks as _checks

                    _orig = getattr(_checks, "check_imshow", None)
                    if _orig is not None:

                        def _noop(*a, **k):
                            return True

                        _checks.check_imshow = _noop
                    try:
                        from ultralytics import solutions

                        for sol_id, sol_name in live_solutions_config:
                            try:
                                if sol_id == "DistanceCalculation":
                                    live_annotators.append(
                                        (
                                            sol_name,
                                            solutions.DistanceCalculation(model=path, show=False),
                                        )
                                    )
                                elif sol_id == "Heatmap":
                                    cmap = getattr(_cv2, _sol_colormap_name, _cv2.COLORMAP_JET)
                                    live_annotators.append(
                                        (
                                            sol_name,
                                            solutions.Heatmap(
                                                model=path, show=False, colormap=cmap
                                            ),
                                        )
                                    )
                                elif sol_id == "ObjectCounter":
                                    live_annotators.append(
                                        (
                                            sol_name,
                                            solutions.ObjectCounter(
                                                model=path, region=_sol_region, show=False
                                            ),
                                        )
                                    )
                                elif sol_id == "RegionCounter":
                                    live_annotators.append(
                                        (
                                            sol_name,
                                            solutions.RegionCounter(
                                                model=path, region=_sol_region, show=False
                                            ),
                                        )
                                    )
                                elif sol_id == "SpeedEstimator":
                                    live_annotators.append(
                                        (
                                            sol_name,
                                            solutions.SpeedEstimator(
                                                model=path, fps=_sol_fps_val, show=False
                                            ),
                                        )
                                    )
                                elif sol_id == "TrackZone":
                                    live_annotators.append(
                                        (
                                            sol_name,
                                            solutions.TrackZone(
                                                model=path, region=_sol_region, show=False
                                            ),
                                        )
                                    )
                            except Exception:
                                import logging

                                logging.getLogger(__name__).debug(
                                    "Detection view update failed", exc_info=True
                                )
                    finally:
                        if _orig is not None:
                            _checks.check_imshow = _orig
                except Exception:
                    import logging

                    logging.getLogger(__name__).debug("Detection view update failed", exc_info=True)

            use_gpu_tensor = use_gpu_tensor_for_preview(backend_id)
            frame_count = 0
            fps_t0 = time.perf_counter()

            def _put_preview(img: np.ndarray) -> None:
                if img is None or img.dtype != np.uint8 or len(img.shape) != 3:
                    return
                # Double-buffer: no copy; producer/consumer use different slots (Part 1.1)
                if use_gpu_tensor:
                    try:
                        import torch

                        if torch.cuda.is_available():
                            payload = torch.from_numpy(img).cuda()
                        else:
                            payload = img
                    except Exception:
                        payload = img
                else:
                    payload = img
                self._preview_buffer.put_nowait(payload)

            # Part 1: Create model in this thread and pre-warm before loop (no lazy creation in predict)
            stdout = _LineEmitter()
            stderr = _LineEmitter()
            try:
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    getattr(self._active_detector, "ensure_model_ready", lambda: None)()
                    while self._run_event.is_set() and self._active_detector.is_loaded:
                        try:
                            frame = self._frame_slot.get(timeout=FRAME_QUEUE_GET_TIMEOUT_S)
                        except Empty:
                            continue
                        t_infer_start = time.perf_counter()
                        try:
                            annotated, _ = self._active_detector.predict(
                                frame, conf=conf_f, iou=iou_f
                            )
                        except Exception:
                            log.warning("predict failed", exc_info=True)
                            annotated = frame
                        self._metrics.set_inference_ms(
                            (time.perf_counter() - t_infer_start) * 1000.0
                        )
                        if (
                            annotated is None
                            or not hasattr(annotated, "shape")
                            or len(annotated.shape) < 3
                        ):
                            continue
                        _ensure_annotators()
                        for sol_name, annotator in live_annotators:
                            try:
                                res = annotator(frame)
                                if res is None:
                                    continue
                                if (
                                    hasattr(res, "plot_im")
                                    and getattr(res, "plot_im", None) is not None
                                ):
                                    plot_im = res.plot_im
                                    if isinstance(plot_im, np.ndarray) and len(plot_im.shape) == 3:
                                        annotated = plot_im
                                elif (
                                    isinstance(res, np.ndarray)
                                    and len(res.shape) == 3
                                    and res.dtype == np.uint8
                                ):
                                    annotated = res
                            except Exception:
                                log.exception("annotator %s", sol_name)
                        _put_preview(annotated)
                        frame_count += 1
                        elapsed = time.perf_counter() - fps_t0
                        if elapsed >= 1.0:
                            try:
                                self._fps_queue.put_nowait(("fps", frame_count / elapsed))
                            except Exception:
                                import logging

                                logging.getLogger(__name__).debug(
                                    "Detection view update failed", exc_info=True
                                )
                            frame_count = 0
                            fps_t0 = time.perf_counter()
            except Exception:
                log.exception("inference_loop")
            finally:
                stdout.flush()
                stderr.flush()
                QTimer.singleShot(0, lambda: self._on_detection_stopped(this_run_id))

        self._inference_thread = Thread(target=inference_loop, daemon=True)
        self._inference_thread.start()
        if self._opencv_source is not None:
            self._capture_thread = Thread(target=capture_loop, daemon=True)
            self._capture_thread.start()
        else:
            # Part 3.9: dedicated capture thread for screen/window (no QTimer on main thread)
            def screen_capture_loop() -> None:
                while self._run_event.is_set() and self._opencv_source is None:
                    t0 = time.perf_counter()
                    frame = None
                    if self._use_full_screen:
                        backend = getattr(self, "_visualization_backend", None)
                        if (
                            backend is not None
                            and getattr(backend, "supports_d3dshot_capture", lambda: False)()
                        ):
                            frame = backend.capture_frame_fullscreen()
                        if frame is None:
                            frame = self._capture.capture_primary_monitor()
                    else:
                        frame = (
                            self._capture.capture_window(self._current_hwnd)
                            if self._current_hwnd
                            else None
                        )
                    self._metrics.set_capture_ms((time.perf_counter() - t0) * 1000.0)
                    if frame is not None:
                        self._frame_slot.put_nowait(frame)
                    time.sleep(CAPTURE_INTERVAL_MS / 1000.0)

            self._screen_capture_thread = Thread(target=screen_capture_loop, daemon=True)
            self._screen_capture_thread.start()

    def _schedule_capture_frame(self) -> None:
        if not self._run_event.is_set() or self._opencv_source is not None:
            return
        try:
            t0 = time.perf_counter()
            frame = None
            if self._use_full_screen:
                backend = getattr(self, "_visualization_backend", None)
                if (
                    backend is not None
                    and getattr(backend, "supports_d3dshot_capture", lambda: False)()
                ):
                    frame = backend.capture_frame_fullscreen()
                if frame is None:
                    frame = self._capture.capture_primary_monitor()
            else:
                frame = (
                    self._capture.capture_window(self._current_hwnd) if self._current_hwnd else None
                )
            self._metrics.set_capture_ms((time.perf_counter() - t0) * 1000.0)
            if frame is not None:
                self._frame_slot.put_nowait(frame)
        except Exception:
            import logging

            logging.getLogger(__name__).debug("Detection view update failed", exc_info=True)

    def _tick_fps(self) -> None:
        while True:
            try:
                msg = self._fps_queue.get_nowait()
                if msg[0] == "fps" and self._run_event.is_set():
                    self._fps_label.setText(f"FPS: {msg[1]:.1f}")
                    if self._detection_job_id is not None:
                        self._container.event_bus.publish(
                            JobProgress(
                                job_id=self._detection_job_id,
                                name="detection",
                                progress=0.5,
                                message=f"fps {msg[1]:.1f}",
                            )
                        )
            except Empty:
                break

    def _on_detection_stopped(self, run_id: int) -> None:
        if run_id != self._run_id:
            return
        self._run_event.clear()
        self._pending_onnx = None
        if self._onnx_export_poll_timer:
            self._onnx_export_poll_timer.stop()
            self._onnx_export_poll_timer = None
        self._capture_timer.stop()
        self._fps_timer.stop()
        backend = getattr(self, "_visualization_backend", None)
        self._visualization_backend = None
        threads = (self._capture_thread, self._screen_capture_thread, self._inference_thread)

        def _blocking_stop() -> None:
            try:
                if backend is not None:
                    backend.stop_display()
            except Exception:
                import logging

                logging.getLogger(__name__).debug("Detection view update failed", exc_info=True)
            for th in threads:
                if th is not None and th.is_alive():
                    th.join(timeout=2.0)
            self.stop_cleanup_done.emit(run_id)

        Thread(target=_blocking_stop, daemon=True).start()

    def _finalize_stop_ui(self, run_id: int) -> None:
        """Вызывается на главном потоке после завершения блокирующей остановки."""
        if run_id != self._run_id:
            return
        self._capture_thread = None
        self._screen_capture_thread = None
        self._inference_thread = None
        if self._opencv_source is not None:
            try:
                self._opencv_source.release()
            except Exception:
                import logging

                logging.getLogger(__name__).debug("Detection view update failed", exc_info=True)
            self._opencv_source = None
        self._fps_label.setText("FPS: —")
        self._frame_slot.clear()
        self._preview_buffer.clear()
        self._container.stop_detection_use_case.execute(
            StopDetectionRequest(detector=self._active_detector, release_cuda_cache=True)
        )
        self._detection_status_label.setText(
            "Загрузите модель и нажмите «Старт». Превью откроется в отдельном окне «YOLO Detection»."
        )
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)

    def get_detection_metrics(self) -> dict[str, float]:
        """Return current pipeline timings (capture_ms, inference_ms, render_ms). Thread-safe."""
        return self._metrics.get_metrics()

    def _stop_detection(self) -> None:
        self._run_event.clear()
        if self._opencv_source is not None:
            try:
                self._opencv_source.release()
            except Exception:
                import logging

                logging.getLogger(__name__).debug("Detection view update failed", exc_info=True)
            self._opencv_source = None
        self._on_detection_stopped(self._run_id)
        if self._detection_job_id is not None:
            self._container.event_bus.publish(
                JobCancelled(job_id=self._detection_job_id, name="detection")
            )
            self._detection_job_id = None

    def shutdown(self) -> None:
        if self._run_event.is_set() or self._visualization_backend is not None:
            self._stop_detection()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.shutdown()
        super().closeEvent(event)
