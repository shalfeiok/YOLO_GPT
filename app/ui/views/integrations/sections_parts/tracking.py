from __future__ import annotations

import webbrowser

from PySide6.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout

from app.application.ports.integrations import CometConfig, DVCConfig, SageMakerConfig
from app.ui.components.buttons import SecondaryButton
from app.ui.components.theme import Tokens
from app.ui.infrastructure.file_dialogs import get_existing_dir, get_open_pt_path

from .common import SectionsCtx, edit_style


def build_comet(ctx: SectionsCtx) -> QGroupBox:
    t = Tokens
    grp = QGroupBox("B. Трекинг экспериментов (Comet ML)")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    grp.setToolTip("Логирование экспериментов обучения в облачный сервис Comet ML.")
    lay = QVBoxLayout(grp)
    cfg = ctx.state.comet

    cb = QCheckBox("Логировать эксперименты в Comet ML")
    cb.setChecked(cfg.enabled)
    lay.addWidget(cb)
    lay.addWidget(QLabel("Comet API Key:"))
    le_key = QLineEdit()
    le_key.setEchoMode(le_key.EchoMode.Password)
    le_key.setText(cfg.api_key)
    le_key.setStyleSheet(edit_style())
    lay.addWidget(le_key)
    lay.addWidget(QLabel("Project Name:"))
    le_proj = QLineEdit()
    le_proj.setText(cfg.project_name)
    le_proj.setStyleSheet(edit_style())
    lay.addWidget(le_proj)

    def _save() -> None:
        ctx.vm.save_comet(
            CometConfig(
                enabled=cb.isChecked(),
                api_key=le_key.text().strip(),
                project_name=le_proj.text().strip(),
                max_image_predictions=cfg.max_image_predictions,
                eval_batch_logging_interval=cfg.eval_batch_logging_interval,
                eval_log_confusion_matrix=cfg.eval_log_confusion_matrix,
                mode=cfg.mode,
            )
        )
        ctx.toast_ok("Сохранено", "Настройки Comet ML сохранены.")

    def _reset() -> None:
        c = ctx.vm.reset_comet()
        cb.setChecked(c.enabled)
        le_key.setText(c.api_key)
        le_proj.setText(c.project_name)
        ctx.toast_ok("Сброс", "Настройки Comet сброшены по умолчанию.")

    row = QHBoxLayout()
    for title, url in (
        ("Подробнее", "https://docs.ultralytics.com/ru/integrations/comet/"),
        ("Открыть панель Comet в браузере", "https://www.comet.com/site/"),
    ):
        b = SecondaryButton(title)
        b.clicked.connect(lambda _=False, u=url: webbrowser.open(u))
        row.addWidget(b)
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
    lay = QVBoxLayout(grp)
    cfg = ctx.state.dvc
    cb = QCheckBox("Включить DVC при обучении")
    cb.setChecked(cfg.enabled)
    lay.addWidget(cb)

    def _save() -> None:
        ctx.vm.save_dvc(DVCConfig(enabled=cb.isChecked()))
        ctx.toast_ok("Сохранено", "Настройки DVC сохранены.")

    def _reset() -> None:
        c = ctx.vm.reset_dvc()
        cb.setChecked(c.enabled)
        ctx.toast_ok("Сброс", "Настройки DVC сброшены.")

    row = QHBoxLayout()
    doc = SecondaryButton("Подробнее")
    doc.clicked.connect(
        lambda: webbrowser.open("https://docs.ultralytics.com/ru/integrations/dvc/")
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


def build_sagemaker(ctx: SectionsCtx) -> QGroupBox:
    t = Tokens
    grp = QGroupBox("D. Amazon SageMaker")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    lay = QVBoxLayout(grp)
    cfg = ctx.state.sagemaker

    lay.addWidget(QLabel("Instance type:"))
    le_inst = QLineEdit()
    le_inst.setText(cfg.instance_type)
    le_inst.setStyleSheet(edit_style())
    lay.addWidget(le_inst)
    lay.addWidget(QLabel("Endpoint name:"))
    le_end = QLineEdit()
    le_end.setText(cfg.endpoint_name)
    le_end.setStyleSheet(edit_style())
    lay.addWidget(le_end)

    lay.addWidget(QLabel("Model path:"))
    row_model = QHBoxLayout()
    le_model = QLineEdit()
    le_model.setText(getattr(cfg, "model_path", ""))
    le_model.setStyleSheet(edit_style())
    row_model.addWidget(le_model, 1)
    b_model = SecondaryButton("Обзор…")
    b_model.clicked.connect(
        lambda: (p := get_open_pt_path(ctx.parent, title="Модель")) and le_model.setText(str(p))
    )
    row_model.addWidget(b_model)
    lay.addLayout(row_model)

    lay.addWidget(QLabel("Template cloned path:"))
    row_tpl = QHBoxLayout()
    le_tpl = QLineEdit()
    le_tpl.setText(getattr(cfg, "template_cloned_path", ""))
    le_tpl.setStyleSheet(edit_style())
    row_tpl.addWidget(le_tpl, 1)
    b_tpl = SecondaryButton("Обзор…")
    b_tpl.clicked.connect(
        lambda: (p := get_existing_dir(ctx.parent, title="Папка шаблона"))
        and le_tpl.setText(str(p))
    )
    row_tpl.addWidget(b_tpl)
    lay.addLayout(row_tpl)

    def _save() -> None:
        ctx.vm.save_sagemaker(
            SageMakerConfig(
                instance_type=le_inst.text().strip(),
                endpoint_name=le_end.text().strip(),
                model_path=le_model.text().strip(),
                template_cloned_path=le_tpl.text().strip(),
            )
        )
        ctx.toast_ok("Сохранено", "Настройки SageMaker сохранены.")

    def _reset() -> None:
        c = ctx.vm.reset_sagemaker()
        le_inst.setText(c.instance_type)
        le_end.setText(c.endpoint_name)
        le_model.setText(getattr(c, "model_path", ""))
        le_tpl.setText(getattr(c, "template_cloned_path", ""))
        ctx.toast_ok("Сброс", "Настройки SageMaker сброшены.")

    row = QHBoxLayout()
    doc = SecondaryButton("Подробнее")
    doc.clicked.connect(
        lambda: webbrowser.open("https://docs.ultralytics.com/ru/integrations/amazon-sagemaker/")
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
