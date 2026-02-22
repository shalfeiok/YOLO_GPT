"""
Вкладка «Датасет»: вверху исходная папка и папка сохранения, ниже — функции по мере надобности,
у каждой параметры и кнопка «Применить», прогресс и уведомление. Тяжёлые задачи в отдельном потоке.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import numpy as np

try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None  # type: ignore


def _require_cv2() -> None:
    if cv2 is None:
        raise ImportError(
            "OpenCV (cv2) is required for this feature. Install with: pip install opencv-python"
        )


from PIL import Image
from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.application.facades.datasets import (
    AUGMENT_OPTIONS,
    draw_boxes,
    get_labels_path_for_image,
    get_sample_image_paths,
    load_classes_from_dataset,
)
from app.config import PROJECT_ROOT
from app.core.events.job_events import JobFailed, JobFinished, JobProgress, JobStarted
from app.core.observability.run_manifest import register_run
from app.ui.components.buttons import PrimaryButton, SecondaryButton
from app.ui.components.inputs import NoWheelSlider
from app.ui.components.photo_preview import show_scrollable_photo_dialog
from app.ui.theme.tokens import Tokens
from app.ui.views.datasets.worker import DatasetWorker

PREVIEW_PHOTOS_COUNT = 6
EFFECT_LABELS: dict[str, str] = {
    "blur": "Размытие",
    "quality": "Хуже качество",
    "color_shift": "Сдвиг цвета",
    "resolution": "Меньше разрешение",
    "overexpose": "Засветить",
    "darken": "Затемнить",
    "desaturate": "Обесцветить",
}

LABEL_WIDTH = 160


def _edit_style(t: type) -> str:
    return (
        f"QLineEdit {{ background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; "
        f"border-radius: {t.radius_sm}px; padding: 6px; }}"
    )


def _card_style(t: type) -> str:
    return (
        f"QFrame {{ background: {t.surface}; border: 1px solid {t.border}; "
        f"border-radius: {t.radius_md}px; padding: {t.space_md}px; }}"
    )


def _progress_style(t: type) -> str:
    return (
        f"QProgressBar {{ border: 1px solid {t.border}; border-radius: {t.radius_sm}px; "
        f"text-align: center; }} QProgressBar::chunk {{ background: {t.primary}; border-radius: 4px; }}"
    )


class DatasetsView(QWidget):
    """Вкладка «Датасет»: общие пути вверху, функции рядами с параметрами и «Применить»."""

    def __init__(self, parent: QWidget | None = None, *, container=None) -> None:
        super().__init__(parent)
        self._container = container
        self._bus = getattr(container, "event_bus", None)
        self._class_names: list[str] = []
        self._class_check_vars: list[QCheckBox] = []
        self._merge_check_vars: list[QCheckBox] = []
        self._worker = DatasetWorker()
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._current_row_id: str | None = None
        self._current_job_id: str | None = None
        self._row_widgets: dict[
            str, tuple[Any, QLabel, Any]
        ] = {}  # row_id -> (progress_bar, status_label, apply_btn)
        self._build_ui()

    def _publish_job_start(self, row_id: str) -> None:
        if self._bus is None:
            return
        self._current_job_id = uuid.uuid4().hex
        self._bus.publish(JobStarted(job_id=self._current_job_id, name=f"dataset:{row_id}"))
        self._bus.publish(
            JobProgress(
                job_id=self._current_job_id,
                name=f"dataset:{row_id}",
                progress=0.0,
                message="started",
            )
        )
        try:
            register_run(
                job_id=self._current_job_id,
                run_type="dataset",
                spec={"action": row_id},
                artifacts={
                    "source": self._src_edit.text().strip(),
                    "output": self._out_edit.text().strip(),
                },
            )
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Failed to create dataset run manifest")

    def _publish_job_done(self, *, success: bool, message: str) -> None:
        if self._bus is None or self._current_job_id is None or self._current_row_id is None:
            return
        name = f"dataset:{self._current_row_id}"
        if success:
            self._bus.publish(
                JobProgress(job_id=self._current_job_id, name=name, progress=1.0, message=message)
            )
            self._bus.publish(JobFinished(job_id=self._current_job_id, name=name, result=None))
        else:
            self._bus.publish(JobFailed(job_id=self._current_job_id, name=name, error=message))
        self._current_job_id = None

    def _build_ui(self) -> None:
        t = Tokens
        layout = QVBoxLayout(self)
        layout.setSpacing(t.space_lg)
        layout.setContentsMargins(t.space_lg, t.space_lg, t.space_lg, t.space_lg)

        # ---- Верх: исходная папка и куда сохранять ----
        top_frame = QFrame()
        top_frame.setStyleSheet(_card_style(t))
        top_layout = QVBoxLayout(top_frame)
        top_layout.setSpacing(t.space_md)

        row_src = QHBoxLayout()
        lbl_src = QLabel("Исходная папка:")
        lbl_src.setMinimumWidth(LABEL_WIDTH)
        lbl_src.setToolTip(
            "Папка с исходными изображениями и метками (или только картинками). Используется всеми функциями ниже."
        )
        self._src_edit = QLineEdit()
        self._src_edit.setPlaceholderText("Путь к датасету или папке с изображениями")
        self._src_edit.setToolTip(
            "Путь к исходному датасету. Поддерживаются разные структуры папок (images, img, labels, annotations и т.д.)."
        )
        self._src_edit.setText(str(PROJECT_ROOT / "dataset"))
        self._src_edit.setStyleSheet(_edit_style(t))
        row_src.addWidget(lbl_src)
        row_src.addWidget(self._src_edit, 1)
        btn_browse_src = SecondaryButton("Обзор…")
        btn_browse_src.setToolTip("Выбрать исходную папку")
        btn_browse_src.clicked.connect(self._browse_src)
        row_src.addWidget(btn_browse_src)
        top_layout.addLayout(row_src)

        row_out = QHBoxLayout()
        lbl_out = QLabel("Куда сохранять:")
        lbl_out.setMinimumWidth(LABEL_WIDTH)
        lbl_out.setToolTip(
            "Папка для сохранения результатов: конвертация в YOLO, аугментация, экспорт по классам."
        )
        self._out_edit = QLineEdit()
        self._out_edit.setPlaceholderText("Выходная папка для конвертации, аугментации, экспорта")
        self._out_edit.setToolTip(
            "Путь, куда будут сохраняться сконвертированные или новые датасеты."
        )
        self._out_edit.setText(str(PROJECT_ROOT / "dataset_yolo"))
        self._out_edit.setStyleSheet(_edit_style(t))
        row_out.addWidget(lbl_out)
        row_out.addWidget(self._out_edit, 1)
        btn_browse_out = SecondaryButton("Обзор…")
        btn_browse_out.setToolTip("Выбрать папку для сохранения")
        btn_browse_out.clicked.connect(self._browse_out)
        row_out.addWidget(btn_browse_out)
        top_layout.addLayout(row_out)

        layout.addWidget(top_frame)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        content = QWidget()
        main = QVBoxLayout(content)
        main.setSpacing(t.space_md)

        # ---- 1. Привести к YOLO ----
        main.addWidget(
            self._make_row(
                "1. Привести к формату YOLO",
                None,
                "prepare_yolo",
                self._on_apply_prepare,
            )
        )

        # ---- 2. Превью с метками ----
        main.addWidget(
            self._make_row(
                "2. Превью датасета (фото с метками)",
                None,
                "preview",
                self._on_apply_preview,
            )
        )

        # ---- 3. Аугментация (эффекты в два ряда для адаптивности) ----
        aug_params = QWidget()
        aug_ly = QVBoxLayout(aug_params)
        aug_ly.setContentsMargins(0, 0, 0, 0)
        self._aug_vars: dict[str, QCheckBox] = {}
        effect_items = [(k, EFFECT_LABELS[k]) for k in EFFECT_LABELS if k in AUGMENT_OPTIONS]
        half = (len(effect_items) + 1) // 2
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.addWidget(QLabel("Эффекты:"))
        for key, label in effect_items[:half]:
            cb = QCheckBox(label)
            self._aug_vars[key] = cb
            row1.addWidget(cb)
        row1.addStretch()
        aug_ly.addLayout(row1)
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        for key, label in effect_items[half:]:
            cb = QCheckBox(label)
            self._aug_vars[key] = cb
            row2.addWidget(cb)
        row2.addWidget(QLabel("Сила %:"))
        self._effect_strength_slider = NoWheelSlider(Qt.Orientation.Horizontal)
        self._effect_strength_slider.setRange(0, 100)
        self._effect_strength_slider.setValue(100)
        self._effect_strength_slider.setMinimumWidth(100)
        self._effect_strength_label = QLabel("100")
        self._effect_strength_slider.valueChanged.connect(
            lambda v: self._effect_strength_label.setText(str(v))
        )
        row2.addWidget(self._effect_strength_slider)
        row2.addWidget(self._effect_strength_label)
        effects_preview_btn = SecondaryButton("Примеры эффектов")
        effects_preview_btn.clicked.connect(self._on_effects_preview)
        row2.addWidget(effects_preview_btn)
        row2.addStretch()
        aug_ly.addLayout(row2)
        main.addWidget(
            self._make_row(
                "3. Создать варианты датасета (размытие, яркость и т.д.)",
                aug_params,
                "augment",
                self._on_apply_augment,
            )
        )

        # ---- 4. Загрузить классы ----
        load_classes_btn = SecondaryButton("Загрузить классы")
        load_classes_btn.clicked.connect(self._load_classes)
        main.addWidget(
            self._make_row(
                "4. Загрузить классы датасета",
                load_classes_btn,
                "load_classes",
                None,
            )
        )

        # ---- Блок: классы для превью и экспорта (виден у превью и у экспорта) ----
        classes_card = QFrame()
        classes_card.setStyleSheet(_card_style(t))
        classes_card_ly = QVBoxLayout(classes_card)
        classes_card_ly.setSpacing(t.space_sm)
        classes_card_ly.addWidget(QLabel("Классы (отметьте для превью и экспорта):"))
        self._class_checks_widget = QWidget()
        # Сетка: чекбоксы переносятся по строкам, без горизонтальной прокрутки
        self._class_checks_layout = QGridLayout(self._class_checks_widget)
        self._class_checks_layout.setContentsMargins(0, 0, 0, 0)
        classes_card_ly.addWidget(self._class_checks_widget)
        main.addWidget(classes_card)

        # ---- 5. Превью с выбранными классами ----
        main.addWidget(
            self._make_row(
                "5. Превью с выбранными классами",
                None,
                "preview_classes",
                self._on_apply_preview_classes,
            )
        )

        # ---- 6. Переименовать класс ----
        rename_row = QHBoxLayout()
        rename_row.setContentsMargins(0, 0, 0, 0)
        self._rename_combo = QComboBox()
        self._rename_combo.setMinimumWidth(140)
        self._rename_combo.setStyleSheet(
            f"QComboBox {{ background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; "
            f"border-radius: {t.radius_sm}px; padding: 4px; }}"
        )
        rename_row.addWidget(QLabel("Класс:"))
        rename_row.addWidget(self._rename_combo)
        rename_row.addWidget(QLabel("Новое имя:"))
        self._rename_new_edit = QLineEdit()
        self._rename_new_edit.setPlaceholderText("имя")
        self._rename_new_edit.setStyleSheet(_edit_style(t))
        self._rename_new_edit.setFixedWidth(120)
        rename_row.addWidget(self._rename_new_edit)
        rename_row.addStretch()
        rename_w = QWidget()
        rename_w.setLayout(rename_row)
        main.addWidget(
            self._make_row(
                "6. Переименовать класс",
                rename_w,
                "rename_class",
                self._on_apply_rename,
            )
        )

        # ---- 7. Экспорт по классам (используются классы из блока выше) ----
        export_hint = QLabel("Используются классы, отмеченные в блоке «Классы» выше.")
        export_hint.setStyleSheet(f"color: {t.text_secondary}; font-size: 12px;")
        main.addWidget(
            self._make_row(
                "7. Экспорт датасета (только выбранные классы)",
                export_hint,
                "export_classes",
                self._on_apply_export,
            )
        )

        # ---- 8. Объединить классы ----
        merge_row = QHBoxLayout()
        merge_row.setContentsMargins(0, 0, 0, 0)
        load_merge_btn = SecondaryButton("Загрузить классы")
        load_merge_btn.clicked.connect(self._load_merge_classes)
        merge_row.addWidget(load_merge_btn)
        merge_row.addWidget(QLabel("Классы для объединения:"))
        self._merge_checks_widget = QWidget()
        self._merge_checks_layout = QHBoxLayout(self._merge_checks_widget)
        self._merge_checks_layout.setContentsMargins(0, 0, 0, 0)
        merge_row.addWidget(self._merge_checks_widget, 1)
        merge_row.addWidget(QLabel("Имя объединённого:"))
        self._merge_name_edit = QLineEdit()
        self._merge_name_edit.setPlaceholderText("например: object")
        self._merge_name_edit.setStyleSheet(_edit_style(t))
        self._merge_name_edit.setFixedWidth(120)
        merge_row.addWidget(self._merge_name_edit)
        merge_w = QWidget()
        merge_w.setLayout(merge_row)
        main.addWidget(
            self._make_row(
                "8. Объединить классы в один",
                merge_w,
                "merge_classes",
                self._on_apply_merge,
            )
        )

        main.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _make_row(
        self,
        title: str,
        params_widget: QWidget | None,
        row_id: str,
        on_apply: callable | None,
    ) -> QFrame:
        t = Tokens
        card = QFrame()
        card.setStyleSheet(_card_style(t))
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(t.space_sm)

        row = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-weight: bold; color: {t.text_primary};")
        title_lbl.setMinimumWidth(280)
        row.addWidget(title_lbl)

        if params_widget:
            row.addWidget(params_widget, 1)
        else:
            row.addStretch(1)

        apply_btn = PrimaryButton("Применить") if on_apply else None
        if apply_btn:
            apply_btn.setMinimumWidth(100)
            apply_btn.clicked.connect(lambda checked=False, r=row_id: self._run_apply(r))
            row.addWidget(apply_btn)
            self._row_widgets[row_id] = (None, None, apply_btn)

        card_layout.addLayout(row)

        progress_bar = None
        status_label = None
        if on_apply and row_id not in ("preview", "preview_classes", "load_classes"):
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 0)  # indeterminate
            progress_bar.setStyleSheet(_progress_style(t))
            progress_bar.setVisible(False)
            card_layout.addWidget(progress_bar)
            status_label = QLabel()
            status_label.setStyleSheet(f"color: {t.text_secondary}; font-size: 12px;")
            status_label.setVisible(False)
            card_layout.addWidget(status_label)
            if row_id in self._row_widgets:
                old = self._row_widgets[row_id]
                self._row_widgets[row_id] = (progress_bar, status_label, old[2])
            else:
                self._row_widgets[row_id] = (progress_bar, status_label, apply_btn)

        return card

    def _run_apply(self, row_id: str) -> None:
        if self._thread.isRunning():
            QMessageBox.warning(self, "Занято", "Дождитесь завершения текущей операции.")
            return
        if row_id == "prepare_yolo":
            self._on_apply_prepare()
        elif row_id == "preview":
            self._on_apply_preview()
        elif row_id == "augment":
            self._on_apply_augment()
        elif row_id == "preview_classes":
            self._on_apply_preview_classes()
        elif row_id == "rename_class":
            self._on_apply_rename()
        elif row_id == "export_classes":
            self._on_apply_export()
        elif row_id == "merge_classes":
            self._on_apply_merge()

    def _set_row_busy(self, row_id: str, busy: bool) -> None:
        if row_id not in self._row_widgets:
            return
        prog, status_lbl, btn = self._row_widgets[row_id]
        if btn:
            btn.setEnabled(not busy)
        if prog is not None:
            prog.setVisible(busy)
            if busy:
                prog.setRange(0, 0)
        if status_lbl is not None and not busy:
            status_lbl.setVisible(False)

    def _show_row_done(self, row_id: str, success: bool, message: str) -> None:
        if row_id not in self._row_widgets:
            return
        prog, status_lbl, btn = self._row_widgets[row_id]
        if prog is not None:
            prog.setVisible(False)
        if status_lbl is not None:
            status_lbl.setVisible(True)
            t = Tokens
            status_lbl.setText("Готово." if success else "Ошибка.")
            status_lbl.setStyleSheet(
                f"color: {t.success}; font-size: 12px;"
                if success
                else f"color: {t.error}; font-size: 12px;"
            )
        if btn is not None:
            btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Готово", message)
        else:
            QMessageBox.critical(self, "Ошибка", message)

    def _on_worker_progress(self, value: float) -> None:
        if self._current_row_id and self._current_row_id in self._row_widgets:
            prog, _, _ = self._row_widgets[self._current_row_id]
            if prog is not None and prog.isVisible():
                prog.setRange(0, 100)
                prog.setValue(int(value * 100))
            if self._bus is not None and self._current_job_id is not None:
                self._bus.publish(
                    JobProgress(
                        job_id=self._current_job_id,
                        name=f"dataset:{self._current_row_id}",
                        progress=max(0.0, min(1.0, value)),
                        message="running",
                    )
                )

    def _on_worker_finished(self, success: bool, message: str) -> None:
        row_id = self._current_row_id
        self._publish_job_done(success=success, message=message)
        self._current_row_id = None
        self._thread.quit()
        if row_id:
            self._set_row_busy(row_id, False)
            self._show_row_done(row_id, success, message)
            if row_id == "rename_class" and success:
                self._rename_new_edit.clear()
                self._load_classes()

    def _start_worker(self, row_id: str, task_id: str, params: dict[str, Any]) -> None:
        self._current_row_id = row_id
        self._publish_job_start(row_id)
        self._set_row_busy(row_id, True)
        self._worker.set_task(task_id, params)
        self._thread.start()

    def _browse_src(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Исходная папка", self._src_edit.text())
        if path:
            self._src_edit.setText(path)

    def _browse_out(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Куда сохранять", self._out_edit.text())
        if path:
            self._out_edit.setText(path)

    def _on_apply_prepare(self) -> None:
        src = self._src_edit.text().strip()
        out = self._out_edit.text().strip()
        self._start_worker("prepare_yolo", "prepare_yolo", {"src": src, "out": out})

    def _on_effects_preview(self) -> None:
        p = Path(self._src_edit.text().strip())
        if not p.is_dir():
            QMessageBox.warning(self, "Ошибка", "Укажите исходную папку датасета.")
            return
        effect_keys = [k for k, cb in self._aug_vars.items() if cb.isChecked()]
        strength = max(0.0, min(100.0, self._effect_strength_slider.value()))
        paths = get_sample_image_paths(p, 1)
        if not paths:
            QMessageBox.warning(self, "Эффекты", "В датасете не найдено изображений.")
            return
        img = cv2.imread(str(paths[0]))
        if img is None:
            QMessageBox.warning(self, "Эффекты", "Не удалось загрузить изображение.")
            return
        t = max(0.0, min(1.0, strength / 100.0))
        items: list[tuple[str, Image.Image]] = [
            ("Оригинал", Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
        ]
        for key in effect_keys:
            if key not in AUGMENT_OPTIONS:
                continue
            transformed = AUGMENT_OPTIONS[key](img)
            if transformed is not None:
                if t < 1.0:
                    blended = (
                        (img.astype(np.float32) * (1 - t) + transformed.astype(np.float32) * t)
                        .clip(0, 255)
                        .astype(np.uint8)
                    )
                else:
                    blended = transformed
                items.append(
                    (
                        EFFECT_LABELS.get(key, key),
                        Image.fromarray(cv2.cvtColor(blended, cv2.COLOR_BGR2RGB)),
                    )
                )
        if len(items) <= 1:
            QMessageBox.warning(self, "Эффекты", "Отметьте хотя бы один эффект.")
            return
        show_scrollable_photo_dialog(self, "Примеры с эффектами", items)

    def _on_apply_preview(self) -> None:
        p = Path(self._src_edit.text().strip())
        if not p.is_dir():
            QMessageBox.warning(self, "Ошибка", "Укажите исходную папку датасета.")
            return
        classes = load_classes_from_dataset(p)
        paths = get_sample_image_paths(p, PREVIEW_PHOTOS_COUNT)
        if not paths:
            QMessageBox.warning(self, "Превью", "В датасете не найдено изображений.")
            return
        images_pil: list[Image.Image] = []
        for img_path in paths:
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            lbl_path = get_labels_path_for_image(p, img_path)
            if lbl_path and lbl_path.exists():
                img = draw_boxes(img, lbl_path, classes, only_classes=None)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            images_pil.append(Image.fromarray(img_rgb))
        if not images_pil:
            QMessageBox.warning(self, "Превью", "Не удалось загрузить изображения.")
            return
        show_scrollable_photo_dialog(self, "Примеры с метками", images_pil)

    def _on_apply_augment(self) -> None:
        src = self._src_edit.text().strip()
        out = self._out_edit.text().strip()
        opts = {k: cb.isChecked() for k, cb in self._aug_vars.items()}
        if not any(opts.values()):
            QMessageBox.warning(self, "Аугментация", "Отметьте хотя бы один эффект.")
            return
        self._start_worker("augment", "augment", {"src": src, "out": out, "opts": opts})

    def _load_classes(self) -> None:
        while self._class_checks_layout.count():
            item = self._class_checks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._class_check_vars.clear()
        p = Path(self._src_edit.text().strip())
        if not p.is_dir():
            self._class_names = []
            self._rename_combo.clear()
            self._rename_combo.addItem("")
            return
        self._class_names = load_classes_from_dataset(p)
        cols = 4
        for i, name in enumerate(self._class_names):
            cb = QCheckBox(name)
            cb.setChecked(True)
            self._class_check_vars.append(cb)
            self._class_checks_layout.addWidget(cb, i // cols, i % cols)
        self._rename_combo.clear()
        self._rename_combo.addItems(self._class_names if self._class_names else [""])
        if self._class_names:
            self._rename_combo.setCurrentIndex(0)
        QMessageBox.information(self, "Готово", f"Загружено классов: {len(self._class_names)}")

    def _on_apply_preview_classes(self) -> None:
        p = Path(self._src_edit.text().strip())
        if not p.is_dir():
            QMessageBox.warning(
                self, "Ошибка", "Укажите исходную папку и при необходимости «Загрузить классы»."
            )
            return
        selected = None
        if self._class_check_vars:
            selected = {i for i, cb in enumerate(self._class_check_vars) if cb.isChecked()}
            if not selected:
                selected = None
        classes = load_classes_from_dataset(p)
        paths = get_sample_image_paths(p, PREVIEW_PHOTOS_COUNT)
        if not paths:
            QMessageBox.warning(self, "Превью", "В датасете не найдено изображений.")
            return
        images_pil = []
        for img_path in paths:
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            lbl_path = get_labels_path_for_image(p, img_path)
            if lbl_path and lbl_path.exists():
                img = draw_boxes(img, lbl_path, classes, only_classes=selected)
            images_pil.append(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
        if not images_pil:
            QMessageBox.warning(self, "Превью", "Не удалось загрузить изображения.")
            return
        show_scrollable_photo_dialog(self, "Примеры (выбранные классы)", images_pil)

    def _on_apply_rename(self) -> None:
        src = self._src_edit.text().strip()
        old_name = self._rename_combo.currentText().strip()
        new_name = self._rename_new_edit.text().strip()
        self._start_worker(
            "rename_class",
            "rename_class",
            {
                "src": src,
                "old_name": old_name,
                "new_name": new_name,
            },
        )

    def _on_apply_export(self) -> None:
        p = Path(self._src_edit.text().strip())
        out = Path(self._out_edit.text().strip())
        if not p.is_dir():
            QMessageBox.warning(self, "Ошибка", "Укажите исходную папку.")
            return
        if not out:
            QMessageBox.warning(self, "Ошибка", "Укажите папку «Куда сохранять».")
            return
        classes = load_classes_from_dataset(p)
        selected = {
            i for i, cb in enumerate(self._class_check_vars) if i < len(classes) and cb.isChecked()
        }
        if not selected:
            QMessageBox.warning(self, "Экспорт", "Загрузите классы и отметьте хотя бы один.")
            return
        self._start_worker(
            "export_classes",
            "export_classes",
            {
                "src": str(p),
                "out": str(out),
                "selected": selected,
                "classes": classes,
            },
        )

    def _on_apply_merge(self) -> None:
        p = Path(self._src_edit.text().strip())
        out = Path(self._out_edit.text().strip())
        if not p.is_dir():
            QMessageBox.warning(self, "Ошибка", "Укажите исходную папку.")
            return
        if not out:
            QMessageBox.warning(self, "Ошибка", "Укажите папку «Куда сохранять».")
            return
        class_names = load_classes_from_dataset(p)
        to_merge = {i for i, cb in enumerate(self._merge_check_vars) if cb.isChecked()}
        if len(to_merge) < 2:
            QMessageBox.warning(
                self,
                "Объединение",
                "Загрузите классы (п.4) и отметьте хотя бы два для объединения.",
            )
            return
        new_name = self._merge_name_edit.text().strip() or "merged"
        self._start_worker(
            "merge_classes",
            "merge_classes",
            {
                "src": str(p),
                "out": str(out),
                "to_merge": to_merge,
                "new_name": new_name,
                "class_names": class_names,
            },
        )

    def _load_merge_classes(self) -> None:
        """Вызывать при смене пути или отдельной кнопкой — классы для объединения."""
        while self._merge_checks_layout.count():
            item = self._merge_checks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._merge_check_vars.clear()
        p = Path(self._src_edit.text().strip())
        if not p.is_dir():
            return
        for name in load_classes_from_dataset(p):
            cb = QCheckBox(name)
            cb.setChecked(False)
            self._merge_check_vars.append(cb)
            self._merge_checks_layout.addWidget(cb)
