from __future__ import annotations

import webbrowser
from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from app.ui.components.buttons import SecondaryButton
from app.ui.components.inputs import NoWheelSpinBox
from app.ui.theme.tokens import Tokens

from .common import edit_style

if TYPE_CHECKING:
    from .advanced_settings_dialog import AdvancedTrainingSettingsDialog


def build_preset_section(
    dlg: AdvancedTrainingSettingsDialog,
    form: QVBoxLayout,
    presets: list[tuple[str, str, dict[str, Any]]],
) -> None:
    t = Tokens
    grp = QGroupBox("Пресеты")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    preset_ly = QVBoxLayout(grp)

    row = QHBoxLayout()
    row.addWidget(QLabel("Сценарий:"))
    dlg._preset_combo = QComboBox()
    dlg._preset_combo.blockSignals(True)
    for name, _desc, _data in presets:
        dlg._preset_combo.addItem(name)
    dlg._preset_combo.setCurrentIndex(0)
    dlg._preset_combo.blockSignals(False)
    dlg._preset_combo.setStyleSheet(edit_style())
    dlg._preset_combo.setToolTip("Выберите готовый набор настроек под типичную задачу.")
    dlg._preset_combo.currentIndexChanged.connect(dlg._on_preset_selected)
    row.addWidget(dlg._preset_combo, 1)
    preset_ly.addLayout(row)

    dlg._preset_desc = QLabel("")
    dlg._preset_desc.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px;")
    dlg._preset_desc.setWordWrap(True)
    preset_ly.addWidget(dlg._preset_desc)

    form.addWidget(grp)
    dlg._update_preset_description()


def build_profile_section(dlg: AdvancedTrainingSettingsDialog, form: QVBoxLayout) -> None:
    t = Tokens
    grp = QGroupBox("Профиль")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    pro_ly = QHBoxLayout(grp)

    pro_ly.addWidget(QLabel("Профиль:"))
    dlg._profile_combo = QComboBox()
    dlg._profile_combo.setEditable(False)
    dlg._profile_combo.setStyleSheet(edit_style())
    dlg._profile_combo.setToolTip(
        "Выберите сохранённый профиль или «Стандартный» для значений по умолчанию."
    )
    dlg._profile_combo.currentTextChanged.connect(dlg._on_profile_selected)
    pro_ly.addWidget(dlg._profile_combo, 1)

    btn_std = SecondaryButton("Стандартный")
    btn_std.setToolTip("Сбросить все параметры к значениям по умолчанию Ultralytics.")
    btn_std.clicked.connect(dlg._load_default_profile)
    pro_ly.addWidget(btn_std)

    btn_save = SecondaryButton("Сохранить как…")
    btn_save.setToolTip("Сохранить текущие настройки под новым именем профиля.")
    btn_save.clicked.connect(dlg._save_profile_as)
    pro_ly.addWidget(btn_save)

    form.addWidget(grp)


def build_albumentations_section(dlg: AdvancedTrainingSettingsDialog, form: QVBoxLayout) -> None:
    t = Tokens
    grp = QGroupBox("Аугментация (Albumentations)")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    grp.setToolTip(
        "Случайные трансформы изображений во время обучения (Blur, CLAHE и др.). "
        "Сохраняется в конфиг интеграций."
    )
    alb_ly = QVBoxLayout(grp)

    dlg._alb_enabled_cb = QCheckBox("Включить Albumentations во время обучения")
    dlg._alb_enabled_cb.setToolTip("Применять аугментацию к каждому батчу при обучении.")
    alb_ly.addWidget(dlg._alb_enabled_cb)

    row1 = QHBoxLayout()
    row1.addWidget(QLabel("Режим:"))
    dlg._alb_mode_combo = QComboBox()
    dlg._alb_mode_combo.addItems(["Стандартные трансформы", "Кастомные трансформы"])
    dlg._alb_mode_combo.setStyleSheet(edit_style())
    dlg._alb_mode_combo.setToolTip("Стандартные — встроенный набор; кастомные — свой список.")
    row1.addWidget(dlg._alb_mode_combo, 1)
    alb_ly.addLayout(row1)

    row2 = QHBoxLayout()
    row2.addWidget(QLabel("Вероятность (p), %:"))
    dlg._alb_p_spin = NoWheelSpinBox()
    dlg._alb_p_spin.setRange(0, 100)
    dlg._alb_p_spin.setValue(50)
    dlg._alb_p_spin.setStyleSheet(edit_style())
    dlg._alb_p_spin.setToolTip("Вероятность применения аугментации к изображению (0–100%).")
    row2.addWidget(dlg._alb_p_spin)
    alb_ly.addLayout(row2)

    dlg._alb_edit_btn = SecondaryButton("Редактировать кастомные трансформы")
    dlg._alb_edit_btn.setToolTip("Добавить/удалить трансформы в режиме «Кастомные трансформы».")
    dlg._alb_edit_btn.clicked.connect(dlg._open_albumentations_transforms_editor)
    alb_ly.addWidget(dlg._alb_edit_btn)

    btn_row = QHBoxLayout()
    doc_btn = SecondaryButton("Подробнее")
    doc_btn.setToolTip("Документация Ultralytics по Albumentations.")
    doc_btn.clicked.connect(
        lambda: webbrowser.open("https://docs.ultralytics.com/ru/integrations/albumentations/")
    )
    reset_btn = SecondaryButton("Сбросить по умолчанию")
    reset_btn.setToolTip("Включить «Стандартные», p=50%, отключить аугментацию.")
    reset_btn.clicked.connect(dlg._reset_albumentations_default)

    btn_row.addWidget(doc_btn)
    btn_row.addWidget(reset_btn)
    btn_row.addStretch()
    alb_ly.addLayout(btn_row)

    form.addWidget(grp)
    dlg._load_albumentations_into_form()


def build_performance_section(dlg: AdvancedTrainingSettingsDialog, form: QVBoxLayout) -> None:
    t = Tokens
    grp = QGroupBox("Производительность и память")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    ly = QFormLayout(grp)

    dlg._cache_cb = QCheckBox("Кэшировать датасет в RAM")
    dlg._cache_cb.setChecked(dlg._values["cache"])
    dlg._cache_cb.setToolTip(
        "Загрузить все изображения в оперативную память. Ускоряет эпохи, но требует много RAM."
    )
    dlg._widgets["cache"] = dlg._cache_cb
    ly.addRow(dlg._cache_cb)

    dlg._amp_cb = QCheckBox("Смешанная точность (AMP)")
    dlg._amp_cb.setChecked(dlg._values["amp"])
    dlg._amp_cb.setToolTip(
        "Использовать автоматическую смешанную точность (FP16) на GPU. Обычно оставлять включённым."
    )
    dlg._widgets["amp"] = dlg._amp_cb
    ly.addRow(dlg._amp_cb)

    form.addWidget(grp)


def build_lr_section(dlg: AdvancedTrainingSettingsDialog, form: QVBoxLayout) -> None:
    t = Tokens
    grp = QGroupBox("Learning rate")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    ly = QFormLayout(grp)

    dlg._lr0 = QDoubleSpinBox()
    dlg._lr0.setRange(0.00001, 1.0)
    dlg._lr0.setDecimals(5)
    dlg._lr0.setSingleStep(0.001)
    dlg._lr0.setValue(dlg._values["lr0"])
    dlg._lr0.setStyleSheet(edit_style())
    dlg._lr0.setToolTip(
        "Начальный learning rate. При optimizer=auto может игнорироваться (подбор авто)."
    )
    dlg._widgets["lr0"] = dlg._lr0
    ly.addRow("Начальный (lr0):", dlg._lr0)

    dlg._lrf = QDoubleSpinBox()
    dlg._lrf.setRange(0.0001, 1.0)
    dlg._lrf.setDecimals(4)
    dlg._lrf.setValue(dlg._values["lrf"])
    dlg._lrf.setStyleSheet(edit_style())
    dlg._lrf.setToolTip("Финальный lr = lr0 * lrf (затухание к концу обучения).")
    dlg._widgets["lrf"] = dlg._lrf
    ly.addRow("Финальный множитель (lrf):", dlg._lrf)

    form.addWidget(grp)


def build_yolo_augmentation_section(
    dlg: AdvancedTrainingSettingsDialog, form: QVBoxLayout
) -> None:
    t = Tokens
    grp = QGroupBox("Встроенная аугментация YOLO")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    ly = QFormLayout(grp)

    dlg._mosaic = QDoubleSpinBox()
    dlg._mosaic.setRange(0.0, 1.0)
    dlg._mosaic.setDecimals(2)
    dlg._mosaic.setSingleStep(0.1)
    dlg._mosaic.setValue(dlg._values["mosaic"])
    dlg._mosaic.setStyleSheet(edit_style())
    dlg._mosaic.setToolTip("Вероятность mosaic (склейка 4 изображений). 0 — отключить.")
    dlg._widgets["mosaic"] = dlg._mosaic
    ly.addRow("Mosaic (0–1):", dlg._mosaic)

    dlg._mixup = QDoubleSpinBox()
    dlg._mixup.setRange(0.0, 1.0)
    dlg._mixup.setDecimals(2)
    dlg._mixup.setValue(dlg._values["mixup"])
    dlg._mixup.setStyleSheet(edit_style())
    dlg._mixup.setToolTip("Вероятность mixup (смешивание двух изображений).")
    dlg._widgets["mixup"] = dlg._mixup
    ly.addRow("MixUp (0–1):", dlg._mixup)

    dlg._close_mosaic = NoWheelSpinBox()
    dlg._close_mosaic.setRange(0, 1000)
    dlg._close_mosaic.setValue(dlg._values["close_mosaic"])
    dlg._close_mosaic.setStyleSheet(edit_style())
    dlg._close_mosaic.setToolTip(
        "За сколько эпох до конца отключить mosaic (стабилизация в конце)."
    )
    dlg._widgets["close_mosaic"] = dlg._close_mosaic
    ly.addRow("Отключить mosaic за (эпох):", dlg._close_mosaic)

    dlg._fliplr = QDoubleSpinBox()
    dlg._fliplr.setRange(0.0, 1.0)
    dlg._fliplr.setDecimals(2)
    dlg._fliplr.setValue(dlg._values["fliplr"])
    dlg._fliplr.setStyleSheet(edit_style())
    dlg._fliplr.setToolTip("Вероятность горизонтального отражения.")
    dlg._widgets["fliplr"] = dlg._fliplr
    ly.addRow("Гориз. отражение (fliplr):", dlg._fliplr)

    dlg._flipud = QDoubleSpinBox()
    dlg._flipud.setRange(0.0, 1.0)
    dlg._flipud.setDecimals(2)
    dlg._flipud.setValue(dlg._values["flipud"])
    dlg._flipud.setStyleSheet(edit_style())
    dlg._flipud.setToolTip("Вероятность вертикального отражения.")
    dlg._widgets["flipud"] = dlg._flipud
    ly.addRow("Верт. отражение (flipud):", dlg._flipud)

    form.addWidget(grp)


def build_repro_section(dlg: AdvancedTrainingSettingsDialog, form: QVBoxLayout) -> None:
    t = Tokens
    grp = QGroupBox("Воспроизводимость")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    ly = QFormLayout(grp)

    dlg._seed = NoWheelSpinBox()
    dlg._seed.setRange(0, 2**31 - 1)
    dlg._seed.setValue(dlg._values["seed"])
    dlg._seed.setStyleSheet(edit_style())
    dlg._seed.setToolTip(
        "Seed для генератора случайных чисел. 0 — случайный seed при каждом запуске."
    )
    dlg._widgets["seed"] = dlg._seed
    ly.addRow("Seed (0 = случайный):", dlg._seed)

    form.addWidget(grp)


def build_loss_section(dlg: AdvancedTrainingSettingsDialog, form: QVBoxLayout) -> None:
    t = Tokens
    grp = QGroupBox("Веса потерь (advanced)")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    ly = QFormLayout(grp)

    dlg._box = QDoubleSpinBox()
    dlg._box.setRange(0.1, 20.0)
    dlg._box.setDecimals(2)
    dlg._box.setValue(dlg._values["box"])
    dlg._box.setStyleSheet(edit_style())
    dlg._box.setToolTip("Вес потери bbox (локализация).")
    dlg._widgets["box"] = dlg._box
    ly.addRow("box:", dlg._box)

    dlg._cls = QDoubleSpinBox()
    dlg._cls.setRange(0.1, 20.0)
    dlg._cls.setDecimals(2)
    dlg._cls.setValue(dlg._values["cls"])
    dlg._cls.setStyleSheet(edit_style())
    dlg._cls.setToolTip("Вес потери классификации.")
    dlg._widgets["cls"] = dlg._cls
    ly.addRow("cls:", dlg._cls)

    dlg._dfl = QDoubleSpinBox()
    dlg._dfl.setRange(0.1, 20.0)
    dlg._dfl.setDecimals(2)
    dlg._dfl.setValue(dlg._values["dfl"])
    dlg._dfl.setStyleSheet(edit_style())
    dlg._dfl.setToolTip("Вес DFL (Distribution Focal Loss).")
    dlg._widgets["dfl"] = dlg._dfl
    ly.addRow("dfl:", dlg._dfl)

    form.addWidget(grp)


def build_geom_hsv_section(dlg: AdvancedTrainingSettingsDialog, form: QVBoxLayout) -> None:
    t = Tokens
    grp = QGroupBox("Геометрия и цвет (HSV)")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    ly = QFormLayout(grp)

    dlg._degrees = QDoubleSpinBox()
    dlg._degrees.setRange(0.0, 360.0)
    dlg._degrees.setValue(dlg._values["degrees"])
    dlg._degrees.setStyleSheet(edit_style())
    dlg._degrees.setToolTip("Диапазон поворота изображения (градусы).")
    dlg._widgets["degrees"] = dlg._degrees
    ly.addRow("Поворот (degrees):", dlg._degrees)

    dlg._translate = QDoubleSpinBox()
    dlg._translate.setRange(0.0, 1.0)
    dlg._translate.setDecimals(2)
    dlg._translate.setValue(dlg._values["translate"])
    dlg._translate.setStyleSheet(edit_style())
    dlg._translate.setToolTip("Сдвиг (доля от размера).")
    dlg._widgets["translate"] = dlg._translate
    ly.addRow("Сдвиг (translate):", dlg._translate)

    dlg._scale = QDoubleSpinBox()
    dlg._scale.setRange(0.0, 1.0)
    dlg._scale.setDecimals(2)
    dlg._scale.setValue(dlg._values["scale"])
    dlg._scale.setStyleSheet(edit_style())
    dlg._scale.setToolTip("Масштаб (доля).")
    dlg._widgets["scale"] = dlg._scale
    ly.addRow("Масштаб (scale):", dlg._scale)

    dlg._hsv_h = QDoubleSpinBox()
    dlg._hsv_h.setRange(0.0, 1.0)
    dlg._hsv_h.setDecimals(3)
    dlg._hsv_h.setValue(dlg._values["hsv_h"])
    dlg._hsv_h.setStyleSheet(edit_style())
    dlg._hsv_h.setToolTip("Оттенок HSV.")
    dlg._widgets["hsv_h"] = dlg._hsv_h
    ly.addRow("HSV Hue:", dlg._hsv_h)

    dlg._hsv_s = QDoubleSpinBox()
    dlg._hsv_s.setRange(0.0, 1.0)
    dlg._hsv_s.setDecimals(2)
    dlg._hsv_s.setValue(dlg._values["hsv_s"])
    dlg._hsv_s.setStyleSheet(edit_style())
    dlg._hsv_s.setToolTip("Насыщенность HSV.")
    dlg._widgets["hsv_s"] = dlg._hsv_s
    ly.addRow("HSV Sat:", dlg._hsv_s)

    dlg._hsv_v = QDoubleSpinBox()
    dlg._hsv_v.setRange(0.0, 1.0)
    dlg._hsv_v.setDecimals(2)
    dlg._hsv_v.setValue(dlg._values["hsv_v"])
    dlg._hsv_v.setStyleSheet(edit_style())
    dlg._hsv_v.setToolTip("Яркость HSV.")
    dlg._widgets["hsv_v"] = dlg._hsv_v
    ly.addRow("HSV Val:", dlg._hsv_v)

    form.addWidget(grp)
