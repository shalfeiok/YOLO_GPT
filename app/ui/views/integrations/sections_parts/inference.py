from __future__ import annotations

import webbrowser

from PySide6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout

from app.application.ports.integrations import EXPORT_FORMATS, ModelExportConfig, SahiConfig, SegIsolationConfig
from app.ui.components.buttons import SecondaryButton
from app.ui.components.theme import Tokens
from app.ui.infrastructure.file_dialogs import get_open_model_or_yaml_path

from .common import SectionsCtx, edit_style

def build_export(ctx: SectionsCtx) -> QGroupBox:
    t = Tokens
    grp = QGroupBox("H. Export")
    grp.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {t.text_primary}; }}")
    grp.setToolTip("Экспорт модели в разные форматы.")
    lay = QVBoxLayout(grp)
    cfg = ctx.state.model_export

    lay.addWidget(QLabel("Модель (.pt) или YAML:"))
    row_m = QHBoxLayout()
    le_model = QLineEdit()
    le_model.setText(getattr(cfg, "weights_path", getattr(cfg, "model_path", "")))
    le_model.setStyleSheet(edit_style())
    row_m.addWidget(le_model, 1)
    pick = SecondaryButton("Обзор…")
    pick.clicked.connect(
        lambda: (p := get_open_model_or_yaml_path(ctx.parent)) and le_model.setText(str(p))
    )
    row_m.addWidget(pick)
    lay.addLayout(row_m)

    lay.addWidget(QLabel("Формат:"))
    cb_fmt = QComboBox()
    cb_fmt.addItems(list(EXPORT_FORMATS))
    if cfg.format in EXPORT_FORMATS:
        cb_fmt.setCurrentText(cfg.format)
    lay.addWidget(cb_fmt)

    lay.addWidget(QLabel("Директория вывода:"))
    row_out = QHBoxLayout()
    le_out = QLineEdit()
    le_out.setText(cfg.output_dir)
    le_out.setStyleSheet(edit_style())
    row_out.addWidget(le_out, 1)
    pick_out = SecondaryButton("Обзор…")
    pick_out.clicked.connect(
        lambda: (p := get_existing_dir(ctx.parent, title="Директория")) and le_out.setText(str(p))
    )
    row_out.addWidget(pick_out)
    lay.addLayout(row_out)

    def _save() -> None:
        c = ModelExportConfig(
            weights_path=le_model.text().strip(),
            format=cb_fmt.currentText(),
            output_dir=le_out.text().strip(),
        )
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

    lay.addWidget(QLabel("Модель (.pt):"))
    row_m = QHBoxLayout()
    le_model = QLineEdit()
    le_model.setText(getattr(cfg, "weights_path", getattr(cfg, "model_path", "")))
    le_model.setStyleSheet(edit_style())
    row_m.addWidget(le_model, 1)
    pick_m = SecondaryButton("Обзор…")
    pick_m.clicked.connect(
        lambda: (p := get_open_pt_path(ctx.parent, title="SAHI модель"))
        and le_model.setText(str(p))
    )
    row_m.addWidget(pick_m)
    lay.addLayout(row_m)

    lay.addWidget(QLabel("Папка с изображениями:"))
    row_src = QHBoxLayout()
    le_src = QLineEdit()
    le_src.setText(cfg.source_dir)
    le_src.setStyleSheet(edit_style())
    row_src.addWidget(le_src, 1)
    pick_src = SecondaryButton("Обзор…")
    pick_src.clicked.connect(
        lambda: (p := get_existing_dir(ctx.parent, title="Папка изображений"))
        and le_src.setText(str(p))
    )
    row_src.addWidget(pick_src)
    lay.addLayout(row_src)

    def _save() -> None:
        c = SahiConfig(
            model_path=le_model.text().strip(),
            source_dir=le_src.text().strip(),
            slice_height=cfg.slice_height,
            slice_width=cfg.slice_width,
            overlap_height_ratio=cfg.overlap_height_ratio,
            overlap_width_ratio=cfg.overlap_width_ratio,
            confidence_threshold=getattr(cfg, "confidence_threshold", 0.4),
        )
        ctx.vm.save_sahi(c)
        ctx.toast_ok("Сохранено", "Настройки SAHI сохранены.")

    def _reset() -> None:
        c = ctx.vm.reset_sahi()
        le_model.setText(c.model_path)
        le_src.setText(c.source_dir)
        ctx.toast_ok("Сброс", "Настройки SAHI сброшены.")

    def _run() -> None:
        if not le_model.text().strip() or not le_src.text().strip():
            ctx.toast_err("Ошибка", "Укажите модель и папку изображений")
            return
        _save()
        ctx.vm.sahi_predict_async(
            SahiConfig(
                model_path=le_model.text().strip(),
                source_dir=le_src.text().strip(),
                slice_height=cfg.slice_height,
                slice_width=cfg.slice_width,
                overlap_height_ratio=cfg.overlap_height_ratio,
                overlap_width_ratio=cfg.overlap_width_ratio,
                confidence_threshold=getattr(cfg, "confidence_threshold", 0.4),
            )
        )
        ctx.toast_ok("Запуск", "SAHI инференс запущен в фоне.")

    row = QHBoxLayout()
    doc = SecondaryButton("Подробнее")
    doc.clicked.connect(
        lambda: webbrowser.open("https://docs.ultralytics.com/ru/guides/sahi-tiled-inference/")
    )
    row.addWidget(doc)
    reset = SecondaryButton("Сбросить по умолчанию")
    reset.clicked.connect(_reset)
    row.addWidget(reset)
    btn = SecondaryButton("Применить настройки")
    btn.clicked.connect(_save)
    row.addWidget(btn)
    run = SecondaryButton("Запустить SAHI")
    run.clicked.connect(_run)
    row.addWidget(run)
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

    lay.addWidget(QLabel("Seg model (.pt):"))
    row_m = QHBoxLayout()
    le_model = QLineEdit()
    le_model.setText(getattr(cfg, "weights_path", getattr(cfg, "model_path", "")))
    le_model.setStyleSheet(edit_style())
    row_m.addWidget(le_model, 1)
    pick_m = SecondaryButton("Обзор…")
    pick_m.clicked.connect(
        lambda: (p := get_open_pt_path(ctx.parent, title="Seg model")) and le_model.setText(str(p))
    )
    row_m.addWidget(pick_m)
    lay.addLayout(row_m)

    lay.addWidget(QLabel("Источник (файл или папка):"))
    le_src = QLineEdit()
    le_src.setText(cfg.source_path)
    le_src.setStyleSheet(edit_style())
    lay.addWidget(le_src)

    lay.addWidget(QLabel("Директория вывода:"))
    row_out = QHBoxLayout()
    le_out = QLineEdit()
    le_out.setText(cfg.output_dir)
    le_out.setStyleSheet(edit_style())
    row_out.addWidget(le_out, 1)
    pick_out = SecondaryButton("Обзор…")
    pick_out.clicked.connect(
        lambda: (p := get_existing_dir(ctx.parent, title="Директория вывода"))
        and le_out.setText(str(p))
    )
    row_out.addWidget(pick_out)
    lay.addLayout(row_out)

    def _save() -> None:
        c = SegIsolationConfig(
            model_path=le_model.text().strip(),
            source_path=le_src.text().strip(),
            output_dir=le_out.text().strip(),
            background=cfg.background,
            crop=cfg.crop,
        )
        ctx.vm.save_seg(c)
        ctx.toast_ok("Сохранено", "Настройки Seg isolation сохранены.")

    def _reset() -> None:
        c = ctx.vm.reset_seg()
        le_model.setText(c.model_path)
        le_src.setText(c.source_path)
        le_out.setText(c.output_dir)
        ctx.toast_ok("Сброс", "Настройки Seg isolation сброшены.")

    def _run() -> None:
        if not le_model.text().strip() or not le_src.text().strip():
            ctx.toast_err("Ошибка", "Укажите модель и источник")
            return
        _save()
        ctx.vm.seg_isolate_async(
            SegIsolationConfig(
                model_path=le_model.text().strip(),
                source_path=le_src.text().strip(),
                output_dir=le_out.text().strip(),
                background=cfg.background,
                crop=cfg.crop,
            )
        )
        ctx.toast_ok("Запуск", "Seg isolation запущен в фоне.")

    row = QHBoxLayout()
    doc = SecondaryButton("Подробнее")
    doc.clicked.connect(
        lambda: webbrowser.open(
            "https://docs.ultralytics.com/ru/guides/isolating-segmentation-objects/"
        )
    )
    row.addWidget(doc)
    reset = SecondaryButton("Сбросить по умолчанию")
    reset.clicked.connect(_reset)
    row.addWidget(reset)
    btn = SecondaryButton("Применить настройки")
    btn.clicked.connect(_save)
    row.addWidget(btn)
    run = SecondaryButton("Запустить Seg isolation")
    run.clicked.connect(_run)
    row.addWidget(run)
    row.addStretch()
    lay.addLayout(row)
    return grp
