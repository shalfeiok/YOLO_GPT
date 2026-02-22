from __future__ import annotations

import webbrowser
from dataclasses import replace

from PySide6.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout

from app.application.ports.integrations import ModelValidationConfig, TuningConfig
from app.ui.components.buttons import SecondaryButton
from app.ui.components.theme import Tokens
from app.ui.infrastructure.file_dialogs import get_open_pt_path, get_open_yaml_path

from .common import SectionsCtx, edit_style


def build_kfold(ctx: SectionsCtx) -> QGroupBox:
    t = Tokens
    grp = QGroupBox("F. K-Fold")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    grp.setToolTip("K-Fold кросс-валидация для обучения.")
    lay = QVBoxLayout(grp)
    cfg = ctx.state.kfold

    cb = QCheckBox("Включить K-Fold")
    cb.setChecked(cfg.enabled)
    lay.addWidget(cb)
    lay.addWidget(QLabel("Количество фолдов:"))
    le_k = QLineEdit()
    le_k.setText(str(getattr(cfg, "k_folds", getattr(cfg, "k", 5))))
    le_k.setStyleSheet(edit_style())
    lay.addWidget(le_k)

    def _save() -> None:
        try:
            k = int(le_k.text().strip() or "0")
        except ValueError:
            ctx.toast_err("Ошибка", "Количество фолдов должно быть числом")
            return
        c = replace(cfg, enabled=cb.isChecked(), k_folds=k)
        ctx.vm.save_kfold(c)
        ctx.toast_ok("Сохранено", "Настройки K-Fold сохранены.")

    def _reset() -> None:
        c = ctx.vm.reset_kfold()
        cb.setChecked(c.enabled)
        le_k.setText(str(getattr(c, "k_folds", getattr(c, "k", 5))))
        ctx.toast_ok("Сброс", "Настройки K-Fold сброшены.")

    row = QHBoxLayout()
    doc = SecondaryButton("Подробнее")
    doc.clicked.connect(
        lambda: webbrowser.open(
            "https://docs.ultralytics.com/ru/guides/hyperparameter-tuning/#k-fold-cross-validation"
        )
    )
    row.addWidget(doc)
    reset = SecondaryButton("Сбросить по умолчанию")
    reset.clicked.connect(_reset)
    row.addWidget(reset)
    btn = SecondaryButton("Применить настройки")
    btn.clicked.connect(_save)
    row.addWidget(btn)
    row.addStretch()
    lay.addLayout(row)
    return grp


def build_tuning(ctx: SectionsCtx) -> QGroupBox:
    t = Tokens
    grp = QGroupBox("G. Hyperparameter Tuning")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    grp.setToolTip("Автоматический подбор гиперпараметров (Ultralytics Tuning).")
    lay = QVBoxLayout(grp)
    cfg = ctx.state.tuning

    cb = QCheckBox("Включить тюнинг")
    cb.setChecked(cfg.enabled)
    lay.addWidget(cb)
    lay.addWidget(QLabel("Iterations:"))
    le_it = QLineEdit()
    le_it.setText(str(cfg.iterations))
    le_it.setStyleSheet(edit_style())
    lay.addWidget(le_it)

    def _save() -> None:
        try:
            it = int(le_it.text().strip() or "0")
        except ValueError:
            ctx.toast_err("Ошибка", "Iterations должно быть числом")
            return
        c = TuningConfig(enabled=cb.isChecked(), iterations=it)
        ctx.vm.save_tuning(c)
        ctx.toast_ok("Сохранено", "Настройки тюнинга сохранены.")

    def _reset() -> None:
        c = ctx.vm.reset_tuning()
        cb.setChecked(c.enabled)
        le_it.setText(str(c.iterations))
        ctx.toast_ok("Сброс", "Настройки тюнинга сброшены.")

    row = QHBoxLayout()
    doc = SecondaryButton("Подробнее")
    doc.clicked.connect(
        lambda: webbrowser.open("https://docs.ultralytics.com/ru/guides/hyperparameter-tuning/")
    )
    row.addWidget(doc)
    reset = SecondaryButton("Сбросить по умолчанию")
    reset.clicked.connect(_reset)
    row.addWidget(reset)
    btn = SecondaryButton("Применить настройки")
    btn.clicked.connect(_save)
    row.addWidget(btn)
    row.addStretch()
    lay.addLayout(row)
    return grp


def build_validation(ctx: SectionsCtx) -> QGroupBox:
    t = Tokens
    grp = QGroupBox("K. Validation")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    grp.setToolTip("Параметры валидации модели.")
    lay = QVBoxLayout(grp)
    cfg = ctx.state.model_validation

    lay.addWidget(QLabel("Model (.pt):"))
    row_m = QHBoxLayout()
    le_model = QLineEdit()
    le_model.setText(getattr(cfg, "weights_path", getattr(cfg, "model_path", "")))
    le_model.setStyleSheet(edit_style())
    row_m.addWidget(le_model, 1)
    pick_m = SecondaryButton("Обзор…")
    pick_m.clicked.connect(
        lambda: (p := get_open_pt_path(ctx.parent, title="Модель")) and le_model.setText(str(p))
    )
    row_m.addWidget(pick_m)
    lay.addLayout(row_m)

    lay.addWidget(QLabel("Dataset YAML:"))
    row_y = QHBoxLayout()
    le_yaml = QLineEdit()
    le_yaml.setText(cfg.data_yaml)
    le_yaml.setStyleSheet(edit_style())
    row_y.addWidget(le_yaml, 1)
    pick_y = SecondaryButton("Обзор…")
    pick_y.clicked.connect(
        lambda: (p := get_open_yaml_path(ctx.parent, title="Dataset YAML"))
        and le_yaml.setText(str(p))
    )
    row_y.addWidget(pick_y)
    lay.addLayout(row_y)

    def _save() -> None:
        c = ModelValidationConfig(
            weights_path=le_model.text().strip(), data_yaml=le_yaml.text().strip()
        )
        ctx.vm.save_validation(c)
        ctx.toast_ok("Сохранено", "Настройки validation сохранены.")

    def _run() -> None:
        if not le_model.text().strip() or not le_yaml.text().strip():
            ctx.toast_err("Ошибка", "Укажите модель и dataset YAML")
            return
        _save()
        ctx.vm.run_validation(model_path=le_model.text().strip(), data_yaml=le_yaml.text().strip())
        ctx.toast_ok("Запуск", "Валидация запущена в фоне.")

    row = QHBoxLayout()
    doc = SecondaryButton("Подробнее")
    doc.clicked.connect(
        lambda: webbrowser.open("https://docs.ultralytics.com/ru/guides/model-evaluation-insights/")
    )
    row.addWidget(doc)
    btn = SecondaryButton("Применить настройки")
    btn.clicked.connect(_save)
    row.addWidget(btn)
    run = SecondaryButton("Запустить валидацию")
    run.clicked.connect(_run)
    row.addWidget(run)
    row.addStretch()
    lay.addLayout(row)
    return grp
