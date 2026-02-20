"""UI section builders for Integrations view.

This module keeps :mod:`app.ui.views.integrations.view` small and readable.
Each function returns a fully wired :class:`~PySide6.QtWidgets.QGroupBox`.
"""

from __future__ import annotations

import webbrowser
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.application.ports.integrations import (
    CometConfig,
    DVCConfig,
    EXPORT_FORMATS,
    KFoldConfig,
    ModelExportConfig,
    ModelValidationConfig,
    SageMakerConfig,
    SahiConfig,
    SegIsolationConfig,
    TuningConfig,
)
from app.ui.components.buttons import SecondaryButton
from app.ui.components.theme import Tokens
from app.ui.infrastructure.file_dialogs import (
    get_existing_dir,
    get_open_model_or_yaml_path,
    get_open_pt_path,
    get_open_yaml_path,
)
from app.ui.views.integrations.view_model import IntegrationsViewModel


def _edit_style() -> str:
    t = Tokens
    return (
        f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; "
        f"border-radius: {t.radius_sm}px; padding: 6px;"
    )


@dataclass(slots=True)
class SectionsCtx:
    parent: QWidget
    vm: IntegrationsViewModel
    state: object  # IntegrationsState (kept as object to avoid circular imports)
    toast_ok: Callable[[str, str], None]
    toast_err: Callable[[str, str], None]


def build_comet(ctx: SectionsCtx) -> QGroupBox:
    t = Tokens
    grp = QGroupBox("B. Трекинг экспериментов (Comet ML)")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    grp.setToolTip("Логирование экспериментов обучения в облачный сервис Comet ML.")
    lay = QVBoxLayout(grp)
    cfg = ctx.state.comet

    cb = QCheckBox("Логировать эксперименты в Comet ML")
    cb.setChecked(cfg.enabled)
    cb.setToolTip("Включить отправку метрик и артефактов в Comet при обучении.")
    lay.addWidget(cb)

    lay.addWidget(QLabel("Comet API Key:"))
    le_key = QLineEdit(); le_key.setEchoMode(le_key.EchoMode.Password)
    le_key.setText(cfg.api_key)
    le_key.setPlaceholderText("Comet API Key")
    le_key.setStyleSheet(_edit_style())
    lay.addWidget(le_key)

    lay.addWidget(QLabel("Project Name:"))
    le_proj = QLineEdit(); le_proj.setText(cfg.project_name)
    le_proj.setStyleSheet(_edit_style())
    lay.addWidget(le_proj)

    def _save() -> None:
        c = CometConfig(
            enabled=cb.isChecked(),
            api_key=le_key.text().strip(),
            project_name=le_proj.text().strip(),
            max_image_predictions=cfg.max_image_predictions,
            eval_batch_logging_interval=cfg.eval_batch_logging_interval,
            eval_log_confusion_matrix=cfg.eval_log_confusion_matrix,
            mode=cfg.mode,
        )
        ctx.vm.save_comet(c)
        ctx.toast_ok("Сохранено", "Настройки Comet ML сохранены.")

    def _reset() -> None:
        c = ctx.vm.reset_comet()
        cb.setChecked(c.enabled)
        le_key.setText(c.api_key)
        le_proj.setText(c.project_name)
        ctx.toast_ok("Сброс", "Настройки Comet сброшены по умолчанию.")

    row = QHBoxLayout()
    doc = SecondaryButton("Подробнее")
    doc.clicked.connect(lambda: webbrowser.open("https://docs.ultralytics.com/ru/integrations/comet/"))
    row.addWidget(doc)
    panel = SecondaryButton("Открыть панель Comet в браузере")
    panel.clicked.connect(lambda: webbrowser.open("https://www.comet.com/site/"))
    row.addWidget(panel)
    reset = SecondaryButton("Сбросить по умолчанию")
    reset.clicked.connect(_reset)
    row.addWidget(reset)
    btn = SecondaryButton("Применить настройки")
    btn.clicked.connect(_save)
    row.addWidget(btn)
    row.addStretch()
    lay.addLayout(row)
    return grp


def build_dvc(ctx: SectionsCtx) -> QGroupBox:
    t = Tokens
    grp = QGroupBox("C. DVC / DVCLive")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    grp.setToolTip("Интеграция с DVC для версионирования данных и метрик при обучении.")
    lay = QVBoxLayout(grp)
    cfg = ctx.state.dvc
    cb = QCheckBox("Включить DVC при обучении")
    cb.setChecked(cfg.enabled)
    lay.addWidget(cb)

    def _save() -> None:
        c = DVCConfig(enabled=cb.isChecked())
        ctx.vm.save_dvc(c)
        ctx.toast_ok("Сохранено", "Настройки DVC сохранены.")

    def _reset() -> None:
        c = ctx.vm.reset_dvc()
        cb.setChecked(c.enabled)
        ctx.toast_ok("Сброс", "Настройки DVC сброшены.")

    row = QHBoxLayout()
    doc = SecondaryButton("Подробнее")
    doc.clicked.connect(lambda: webbrowser.open("https://docs.ultralytics.com/ru/integrations/dvc/"))
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


def build_sagemaker(ctx: SectionsCtx) -> QGroupBox:
    t = Tokens
    grp = QGroupBox("D. Amazon SageMaker")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    grp.setToolTip("Параметры для развёртывания и обучения на Amazon SageMaker.")
    lay = QVBoxLayout(grp)
    cfg = ctx.state.sagemaker

    lay.addWidget(QLabel("Instance type:"))
    le_inst = QLineEdit(); le_inst.setText(cfg.instance_type); le_inst.setStyleSheet(_edit_style())
    lay.addWidget(le_inst)
    lay.addWidget(QLabel("Endpoint name:"))
    le_end = QLineEdit(); le_end.setText(cfg.endpoint_name); le_end.setStyleSheet(_edit_style())
    lay.addWidget(le_end)

    # optional extras
    lay.addWidget(QLabel("Model path:"))
    row_model = QHBoxLayout()
    le_model = QLineEdit(); le_model.setText(getattr(cfg, 'model_path', '')); le_model.setStyleSheet(_edit_style())
    row_model.addWidget(le_model, 1)
    b_model = SecondaryButton("Обзор…")
    b_model.clicked.connect(lambda: (p := get_open_pt_path(ctx.parent, title="Модель")) and le_model.setText(str(p)))
    row_model.addWidget(b_model)
    lay.addLayout(row_model)

    lay.addWidget(QLabel("Template cloned path:"))
    row_tpl = QHBoxLayout()
    le_tpl = QLineEdit(); le_tpl.setText(getattr(cfg, 'template_cloned_path', '')); le_tpl.setStyleSheet(_edit_style())
    row_tpl.addWidget(le_tpl, 1)
    b_tpl = SecondaryButton("Обзор…")
    b_tpl.clicked.connect(lambda: (p := get_existing_dir(ctx.parent, title="Папка шаблона")) and le_tpl.setText(str(p)))
    row_tpl.addWidget(b_tpl)
    lay.addLayout(row_tpl)

    def _save() -> None:
        c = SageMakerConfig(
            instance_type=le_inst.text().strip(),
            endpoint_name=le_end.text().strip(),
            model_path=le_model.text().strip(),
            template_cloned_path=le_tpl.text().strip(),
        )
        ctx.vm.save_sagemaker(c)
        ctx.toast_ok("Сохранено", "Настройки SageMaker сохранены.")

    def _reset() -> None:
        c = ctx.vm.reset_sagemaker()
        le_inst.setText(c.instance_type)
        le_end.setText(c.endpoint_name)
        le_model.setText(getattr(c, 'model_path', ''))
        le_tpl.setText(getattr(c, 'template_cloned_path', ''))
        ctx.toast_ok("Сброс", "Настройки SageMaker сброшены.")

    row = QHBoxLayout()
    doc = SecondaryButton("Подробнее")
    doc.clicked.connect(lambda: webbrowser.open("https://docs.ultralytics.com/ru/integrations/amazon-sagemaker/"))
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
    le_k = QLineEdit(); le_k.setText(str(getattr(cfg, 'k_folds', getattr(cfg, 'k', 5)))); le_k.setStyleSheet(_edit_style())
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
        le_k.setText(str(getattr(c, 'k_folds', getattr(c, 'k', 5))))
        ctx.toast_ok("Сброс", "Настройки K-Fold сброшены.")

    row = QHBoxLayout()
    doc = SecondaryButton("Подробнее")
    doc.clicked.connect(lambda: webbrowser.open("https://docs.ultralytics.com/ru/guides/hyperparameter-tuning/#k-fold-cross-validation"))
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
    le_it = QLineEdit(); le_it.setText(str(cfg.iterations)); le_it.setStyleSheet(_edit_style())
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
    doc.clicked.connect(lambda: webbrowser.open("https://docs.ultralytics.com/ru/guides/hyperparameter-tuning/"))
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


def build_export(ctx: SectionsCtx) -> QGroupBox:
    t = Tokens
    grp = QGroupBox("H. Export")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    grp.setToolTip("Экспорт модели в разные форматы.")
    lay = QVBoxLayout(grp)
    cfg = ctx.state.model_export

    lay.addWidget(QLabel("Модель (.pt) или YAML:"))
    row_m = QHBoxLayout()
    le_model = QLineEdit(); le_model.setText(getattr(cfg, "weights_path", getattr(cfg, "model_path", ""))); le_model.setStyleSheet(_edit_style())
    row_m.addWidget(le_model, 1)
    pick = SecondaryButton("Обзор…")
    pick.clicked.connect(lambda: (p := get_open_model_or_yaml_path(ctx.parent)) and le_model.setText(str(p)))
    row_m.addWidget(pick)
    lay.addLayout(row_m)

    lay.addWidget(QLabel("Формат:"))
    cb_fmt = QComboBox(); cb_fmt.addItems(list(EXPORT_FORMATS))
    if cfg.format in EXPORT_FORMATS:
        cb_fmt.setCurrentText(cfg.format)
    lay.addWidget(cb_fmt)

    lay.addWidget(QLabel("Директория вывода:"))
    row_out = QHBoxLayout()
    le_out = QLineEdit(); le_out.setText(cfg.output_dir); le_out.setStyleSheet(_edit_style())
    row_out.addWidget(le_out, 1)
    pick_out = SecondaryButton("Обзор…")
    pick_out.clicked.connect(lambda: (p := get_existing_dir(ctx.parent, title="Директория")) and le_out.setText(str(p)))
    row_out.addWidget(pick_out)
    lay.addLayout(row_out)

    def _save() -> None:
        c = ModelExportConfig(weights_path=le_model.text().strip(), format=cb_fmt.currentText(), output_dir=le_out.text().strip())
        ctx.vm.save_export(c)
        ctx.toast_ok("Сохранено", "Настройки экспорта сохранены.")

    def _reset() -> None:
        c = ctx.vm.reset_export()
        le_model.setText(getattr(c, "weights_path", getattr(c, "model_path", "")))
        cb_fmt.setCurrentText(c.format)
        le_out.setText(c.output_dir)
        ctx.toast_ok("Сброс", "Настройки экспорта сброшены.")

    def _run() -> None:
        path = le_model.text().strip()
        if not path:
            ctx.toast_err("Ошибка", "Укажите путь к модели")
            return
        out = le_out.text().strip() or str(Path(path).parent)
        ctx.vm.run_export(model_path=path, export_format=cb_fmt.currentText(), output_dir=out)
        ctx.toast_ok("Запуск", "Экспорт запущен в фоне.")

    row = QHBoxLayout()
    doc = SecondaryButton("Подробнее")
    doc.clicked.connect(lambda: webbrowser.open("https://docs.ultralytics.com/ru/modes/export/"))
    row.addWidget(doc)
    reset = SecondaryButton("Сбросить по умолчанию")
    reset.clicked.connect(_reset)
    row.addWidget(reset)
    btn = SecondaryButton("Применить настройки")
    btn.clicked.connect(_save)
    row.addWidget(btn)
    run = SecondaryButton("Запустить экспорт")
    run.clicked.connect(_run)
    row.addWidget(run)
    row.addStretch()
    lay.addLayout(row)
    return grp


def build_sahi(ctx: SectionsCtx) -> QGroupBox:
    t = Tokens
    grp = QGroupBox("I. SAHI")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    grp.setToolTip("Slicing Aided Hyper Inference (SAHI) для детекции.")
    lay = QVBoxLayout(grp)
    cfg = ctx.state.sahi
    cb = QCheckBox("Включить SAHI")
    cb.setChecked(cfg.enabled)
    lay.addWidget(cb)

    def _save() -> None:
        c = SahiConfig(enabled=cb.isChecked())
        ctx.vm.save_sahi(c)
        ctx.toast_ok("Сохранено", "Настройки SAHI сохранены.")

    def _reset() -> None:
        c = ctx.vm.reset_sahi()
        cb.setChecked(c.enabled)
        ctx.toast_ok("Сброс", "Настройки SAHI сброшены.")

    row = QHBoxLayout()
    doc = SecondaryButton("Подробнее")
    doc.clicked.connect(lambda: webbrowser.open("https://docs.ultralytics.com/ru/guides/sahi-tiled-inference/"))
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


def build_seg_isolation(ctx: SectionsCtx) -> QGroupBox:
    t = Tokens
    grp = QGroupBox("J. Seg isolation")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    grp.setToolTip("Изоляция сегментированных объектов на изображении.")
    lay = QVBoxLayout(grp)
    cfg = ctx.state.seg_isolation
    cb = QCheckBox("Включить изоляцию сегментации")
    cb.setChecked(cfg.enabled)
    lay.addWidget(cb)

    def _save() -> None:
        c = SegIsolationConfig(enabled=cb.isChecked())
        ctx.vm.save_seg(c)
        ctx.toast_ok("Сохранено", "Настройки Seg isolation сохранены.")

    def _reset() -> None:
        c = ctx.vm.reset_seg()
        cb.setChecked(c.enabled)
        ctx.toast_ok("Сброс", "Настройки Seg isolation сброшены.")

    row = QHBoxLayout()
    doc = SecondaryButton("Подробнее")
    doc.clicked.connect(lambda: webbrowser.open("https://docs.ultralytics.com/ru/guides/isolating-segmentation-objects/"))
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
    le_model = QLineEdit(); le_model.setText(cfg.model_path); le_model.setStyleSheet(_edit_style())
    row_m.addWidget(le_model, 1)
    pick_m = SecondaryButton("Обзор…")
    pick_m.clicked.connect(lambda: (p := get_open_pt_path(ctx.parent, title="Модель")) and le_model.setText(str(p)))
    row_m.addWidget(pick_m)
    lay.addLayout(row_m)

    lay.addWidget(QLabel("Dataset YAML:"))
    row_y = QHBoxLayout()
    le_yaml = QLineEdit(); le_yaml.setText(cfg.data_yaml); le_yaml.setStyleSheet(_edit_style())
    row_y.addWidget(le_yaml, 1)
    pick_y = SecondaryButton("Обзор…")
    pick_y.clicked.connect(lambda: (p := get_open_yaml_path(ctx.parent, title="Dataset YAML")) and le_yaml.setText(str(p)))
    row_y.addWidget(pick_y)
    lay.addLayout(row_y)

    def _save() -> None:
        c = ModelValidationConfig(model_path=le_model.text().strip(), data_yaml=le_yaml.text().strip())
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
    doc.clicked.connect(lambda: webbrowser.open("https://docs.ultralytics.com/ru/guides/model-evaluation-insights/"))
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
