"""
Диалог «Расширенные настройки обучения»: cache, lr, mosaic, mixup, seed, веса потерь и др.
Сохранение/загрузка профилей, стандартный профиль по умолчанию.
"""
from __future__ import annotations

import json
import webbrowser
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.config import PROJECT_ROOT
from app.ui.components.buttons import PrimaryButton, SecondaryButton
from app.ui.components.inputs import NoWheelSpinBox
from app.ui.theme.tokens import Tokens
from app.ui.views.training.advanced_settings.common import edit_style
from app.ui.views.training.advanced_settings.sections import (
    build_albumentations_section,
    build_geom_hsv_section,
    build_loss_section,
    build_lr_section,
    build_performance_section,
    build_preset_section,
    build_profile_section,
    build_repro_section,
    build_yolo_augmentation_section,
)

PROFILES_PATH = PROJECT_ROOT / "training_advanced_profiles.json"

# Значения по умолчанию (стандартный профиль Ultralytics)
DEFAULTS: dict[str, Any] = {
    "cache": False,
    "amp": True,
    "lr0": 0.01,
    "lrf": 0.01,
    "mosaic": 1.0,
    "mixup": 0.0,
    "close_mosaic": 10,
    "seed": 0,
    "fliplr": 0.5,
    "flipud": 0.0,
    "box": 7.5,
    "cls": 0.5,
    "dfl": 1.5,
    "degrees": 0.0,
    "translate": 0.1,
    "scale": 0.5,
    "shear": 0.0,
    "perspective": 0.0,
    "hsv_h": 0.015,
    "hsv_s": 0.7,
    "hsv_v": 0.4,
    "warmup_epochs": 3.0,
    "warmup_momentum": 0.8,
    "warmup_bias_lr": 0.1,
    "weight_decay": 0.0005,
}


def _merge_preset(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Скопировать base и перезаписать ключами из overrides."""
    out = dict(base)
    for k, v in overrides.items():
        if k in out:
            out[k] = v
    return out


# Встроенные пресеты «на все случаи жизни»
PRESETS: list[tuple[str, str, dict[str, Any]]] = [
    (
        "Стандартный",
        "Рекомендуемые настройки Ultralytics по умолчанию.",
        DEFAULTS,
    ),
    (
        "Быстрое обучение",
        "Кэш в RAM, полная аугментация. Быстрее эпохи при достаточной памяти.",
        _merge_preset(DEFAULTS, {"cache": True, "mosaic": 1.0, "mixup": 0.0}),
    ),
    (
        "Максимальное качество",
        "Меньше lr, больше mixup и аугментации. Для финального обучения на большом датасете.",
        _merge_preset(DEFAULTS, {
            "lr0": 0.001,
            "lrf": 0.01,
            "mosaic": 1.0,
            "mixup": 0.15,
            "close_mosaic": 5,
            "degrees": 10.0,
            "translate": 0.15,
            "scale": 0.5,
            "hsv_h": 0.02,
            "hsv_s": 0.8,
            "hsv_v": 0.4,
        }),
    ),
    (
        "Экономия памяти",
        "Без кэша, ослабленный mosaic. Для слабого GPU или большого разрешения.",
        _merge_preset(DEFAULTS, {"cache": False, "mosaic": 0.5, "mixup": 0.0, "close_mosaic": 5}),
    ),
    (
        "Воспроизводимость",
        "Фиксированный seed для повторяемых экспериментов.",
        _merge_preset(DEFAULTS, {"seed": 42}),
    ),
    (
        "Сильная аугментация",
        "Максимум геометрии и цветов. Для разнообразия данных и регуляризации.",
        _merge_preset(DEFAULTS, {
            "mosaic": 1.0,
            "mixup": 0.2,
            "degrees": 15.0,
            "translate": 0.2,
            "scale": 0.5,
            "fliplr": 0.5,
            "flipud": 0.1,
            "hsv_h": 0.025,
            "hsv_s": 0.8,
            "hsv_v": 0.45,
        }),
    ),
    (
        "Слабая аугментация",
        "Минимум трансформаций. Маленький датасет или предобученные веса.",
        _merge_preset(DEFAULTS, {
            "mosaic": 0.3,
            "mixup": 0.0,
            "degrees": 0.0,
            "translate": 0.05,
            "scale": 0.3,
            "hsv_h": 0.01,
            "hsv_s": 0.5,
            "hsv_v": 0.3,
        }),
    ),
    (
        "Fine-tuning",
        "Низкий lr, слабая аугментация. Дообучение готовой модели на своих данных.",
        _merge_preset(DEFAULTS, {
            "lr0": 0.001,
            "lrf": 0.01,
            "mosaic": 0.2,
            "mixup": 0.0,
            "close_mosaic": 15,
            "degrees": 0.0,
            "translate": 0.05,
            "scale": 0.3,
        }),
    ),
    (
        "Отладка / быстрый прогон",
        "Почти без аугментации. Проверка пайплайна и быстрая переобучение на малых эпохах.",
        _merge_preset(DEFAULTS, {
            "cache": False,
            "mosaic": 0.0,
            "mixup": 0.0,
            "close_mosaic": 0,
            "degrees": 0.0,
            "translate": 0.0,
            "scale": 0.2,
            "fliplr": 0.5,
            "flipud": 0.0,
        }),
    ),
    (
        "Большой датасет",
        "Кэш, сильная аугментация. Когда данных много и нужна регуляризация.",
        _merge_preset(DEFAULTS, {
            "cache": True,
            "mosaic": 1.0,
            "mixup": 0.1,
            "degrees": 10.0,
            "translate": 0.15,
            "hsv_s": 0.8,
            "hsv_v": 0.4,
        }),
    ),
    (
        "Мелкие объекты",
        "Mosaic и масштаб для лучшего обнаружения мелких целей.",
        _merge_preset(DEFAULTS, {
            "mosaic": 1.0,
            "mixup": 0.1,
            "scale": 0.6,
            "translate": 0.15,
            "close_mosaic": 5,
        }),
    ),
]


def _edit_style() -> str:
    return edit_style()


def load_profiles() -> dict[str, dict[str, Any]]:
    """Загрузить словарь профилей из JSON."""
    if not PROFILES_PATH.exists():
        return {}
    try:
        with open(PROFILES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        profiles = data.get("profiles", {})
        return profiles if isinstance(profiles, dict) else {}
    except Exception:
        return {}


def save_profiles(profiles: dict[str, dict[str, Any]], last_used: str | None = None) -> None:
    """Сохранить профили в JSON."""
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump({"profiles": profiles, "last_used": last_used}, f, ensure_ascii=False, indent=2)


def get_last_used_profile_name() -> str | None:
    """Имя последнего использованного профиля."""
    if not PROFILES_PATH.exists():
        return None
    try:
        with open(PROFILES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            value = data.get("last_used")
            return str(value) if value is not None else None
        return None
    except Exception:
        return None


class AdvancedTrainingSettingsDialog(QDialog):
    """Окно расширенных настроек с профилями."""

    def __init__(self, initial: dict[str, Any] | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Расширенные настройки обучения")
        self.setMinimumSize(520, 620)
        self._values: dict[str, Any] = dict(DEFAULTS)
        if initial:
            for k, v in initial.items():
                if k in self._values:
                    self._values[k] = v
        self._widgets: dict[str, QWidget] = {}
        self._build_ui()
        self._load_profiles_combo()
        last = get_last_used_profile_name()
        if last and last in load_profiles():
            self._profile_combo.setCurrentText(last)  # _on_profile_selected применит профиль

    def _build_ui(self) -> None:
        """Собрать UI диалога.

        Большая часть UI вынесена в app/ui/views/training/advanced_settings/sections.py,
        чтобы файл диалога оставался компактным и поддерживаемым.
        """
        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        form = QVBoxLayout(content)

        build_preset_section(self, form, PRESETS)
        build_profile_section(self, form)
        build_albumentations_section(self, form)
        build_performance_section(self, form)
        build_lr_section(self, form)
        build_yolo_augmentation_section(self, form)
        build_repro_section(self, form)
        build_loss_section(self, form)
        build_geom_hsv_section(self, form)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(self._gather_and_accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    def _load_albumentations_into_form(self) -> None:
        """Загрузить настройки Albumentations из конфига в форму."""
        from app.features.albumentations_integration.repository import load_albumentations_config
        cfg = load_albumentations_config()
        self._alb_enabled_cb.setChecked(cfg.enabled)
        self._alb_mode_combo.setCurrentIndex(0 if cfg.use_standard else 1)
        self._alb_p_spin.setValue(int(cfg.transform_p * 100))

    def _save_albumentations_from_form(self) -> None:
        """Сохранить значения формы Albumentations в конфиг интеграций."""
        from app.features.albumentations_integration.repository import load_albumentations_config, save_albumentations_config
        from app.features.albumentations_integration.domain import AlbumentationsConfig
        cfg = load_albumentations_config()
        cfg.enabled = self._alb_enabled_cb.isChecked()
        cfg.use_standard = self._alb_mode_combo.currentIndex() == 0
        cfg.transform_p = self._alb_p_spin.value() / 100.0
        save_albumentations_config(cfg)

    def _reset_albumentations_default(self) -> None:
        """Сбросить настройки Albumentations к умолчанию в форме."""
        from app.features.albumentations_integration.domain import AlbumentationsConfig
        from app.features.albumentations_integration.repository import save_albumentations_config
        save_albumentations_config(AlbumentationsConfig(enabled=False, use_standard=True, custom_transforms=[], transform_p=0.5))
        self._alb_enabled_cb.setChecked(False)
        self._alb_mode_combo.setCurrentIndex(0)
        self._alb_p_spin.setValue(50)
        QMessageBox.information(self, "Albumentations", "Настройки сброшены по умолчанию.")

    def _open_albumentations_transforms_editor(self) -> None:
        """Диалог редактирования кастомных трансформов Albumentations."""
        from app.features.albumentations_integration.repository import load_albumentations_config, save_albumentations_config
        from app.features.albumentations_integration.domain import STANDARD_TRANSFORM_NAMES
        t = Tokens
        cfg = load_albumentations_config()
        transforms: list = list(cfg.custom_transforms)

        dlg = QDialog(self)
        dlg.setWindowTitle("Кастомные трансформы Albumentations")
        dlg.setMinimumSize(420, 320)
        main_layout = QVBoxLayout(dlg)
        main_layout.addWidget(QLabel("Кастомные трансформы (применяются при обучении):"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)

        def _clear_layout(container: QVBoxLayout) -> None:
            while container.count():
                item = container.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
                else:
                    child_layout = item.layout()
                    if child_layout is not None:
                        while child_layout.count():
                            sub = child_layout.takeAt(0)
                            if sub.widget() is not None:
                                sub.widget().deleteLater()
                        child_layout.deleteLater()

        def refresh_list() -> None:
            _clear_layout(list_layout)
            for i, tr in enumerate(transforms):
                name = tr.get("name", tr.get("transform", "?"))
                p_val = tr.get("p", 0.5)
                row = QHBoxLayout()
                row.addWidget(QLabel(name))
                row.addWidget(QLabel(f"p={p_val}"))
                row.addStretch()
                del_btn = SecondaryButton("Удалить")
                idx = i
                del_btn.clicked.connect(lambda checked=False, ix=idx: _remove(ix))
                row.addWidget(del_btn)
                list_layout.addLayout(row)

        def _remove(idx: int) -> None:
            if 0 <= idx < len(transforms):
                transforms.pop(idx)
                refresh_list()

        def add_transform() -> None:
            add_dlg = QDialog(dlg)
            add_dlg.setWindowTitle("Добавить трансформ")
            form_d = QFormLayout(add_dlg)
            name_combo = QComboBox()
            name_combo.addItems(STANDARD_TRANSFORM_NAMES)
            name_combo.setStyleSheet(f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 4px;")
            form_d.addRow("Трансформ:", name_combo)
            p_spin = NoWheelSpinBox()
            p_spin.setRange(0, 100)
            p_spin.setValue(50)
            p_spin.setStyleSheet(_edit_style())
            form_d.addRow("p (0–1):", p_spin)
            btn_row = QHBoxLayout()
            ok_btn = PrimaryButton("Добавить")
            cancel_btn = SecondaryButton("Отмена")
            def do_add() -> None:
                transforms.append({"name": name_combo.currentText(), "p": p_spin.value() / 100.0})
                refresh_list()
                add_dlg.accept()
            ok_btn.clicked.connect(do_add)
            cancel_btn.clicked.connect(add_dlg.reject)
            btn_row.addWidget(ok_btn)
            btn_row.addWidget(cancel_btn)
            form_d.addRow(btn_row)
            add_dlg.exec()

        refresh_list()
        scroll.setWidget(list_widget)
        main_layout.addWidget(scroll)
        add_btn = SecondaryButton("+ Добавить трансформ")
        add_btn.clicked.connect(add_transform)
        main_layout.addWidget(add_btn)
        save_close_btn = PrimaryButton("Сохранить и закрыть")
        def save_and_close() -> None:
            cfg.custom_transforms = transforms
            save_albumentations_config(cfg)
            dlg.accept()
        save_close_btn.clicked.connect(save_and_close)
        main_layout.addWidget(save_close_btn)
        dlg.exec()

    def _update_preset_description(self) -> None:
        idx = self._preset_combo.currentIndex()
        if 0 <= idx < len(PRESETS):
            self._preset_desc.setText(PRESETS[idx][1])

    def _on_preset_selected(self, index: int) -> None:
        if index < 0 or index >= len(PRESETS):
            return
        self._apply_profile_to_form(PRESETS[index][2])
        self._update_preset_description()

    def _load_profiles_combo(self) -> None:
        self._profile_combo.clear()
        self._profile_combo.addItem("Стандартный")
        for name in sorted(load_profiles().keys()):
            self._profile_combo.addItem(name)

    def _on_profile_selected(self, name: str) -> None:
        if name == "Стандартный":
            self._load_default_profile()
            return
        profiles = load_profiles()
        if name in profiles:
            self._apply_profile_to_form(profiles[name])

    def _apply_profile_to_form(self, data: dict[str, Any]) -> None:
        for key, value in data.items():
            if key not in self._widgets:
                continue
            w = self._widgets[key]
            if isinstance(w, QCheckBox):
                w.setChecked(bool(value))
            elif isinstance(w, NoWheelSpinBox):
                w.setValue(int(value) if isinstance(value, (int, float)) else 0)
            elif hasattr(w, "setValue"):
                w.setValue(float(value) if isinstance(value, (int, float)) else 0)

    def _load_default_profile(self) -> None:
        self._profile_combo.blockSignals(True)
        idx = self._profile_combo.findText("Стандартный")
        if idx >= 0:
            self._profile_combo.setCurrentIndex(idx)
        self._profile_combo.blockSignals(False)
        self._apply_profile_to_form(DEFAULTS)

    def _save_profile_as(self) -> None:
        name, ok = QInputDialog.getText(self, "Сохранить профиль", "Имя профиля:")
        if not ok or not name or not name.strip():
            return
        name = name.strip()
        profiles = load_profiles()
        profiles[name] = self._gather_values()
        save_profiles(profiles, last_used=name)
        self._load_profiles_combo()
        idx = self._profile_combo.findText(name)
        if idx >= 0:
            self._profile_combo.setCurrentIndex(idx)
        QMessageBox.information(self, "Профиль", f"Профиль «{name}» сохранён.")

    def _gather_values(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, w in self._widgets.items():
            if isinstance(w, QCheckBox):
                out[key] = w.isChecked()
            elif isinstance(w, NoWheelSpinBox):
                out[key] = w.value()
            elif hasattr(w, "value"):
                out[key] = w.value()
        return out

    def _gather_and_accept(self) -> None:
        self._save_albumentations_from_form()
        self._values = self._gather_values()
        profiles = load_profiles()
        current = self._profile_combo.currentText()
        if current and current != "Стандартный":
            save_profiles(profiles, last_used=current)
        self.accept()

    def get_values(self) -> dict[str, Any]:
        """Вернуть собранные значения (после accept)."""
        return dict(self._values)
