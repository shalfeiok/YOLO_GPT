from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QTextEdit, QVBoxLayout, QWidget

from app.config import INTEGRATIONS_CONFIG_PATH
from app.ui.components.buttons import SecondaryButton
from app.ui.theme.tokens import Tokens
from app.ui.views.integrations.sections import (
    SectionsCtx,
    build_comet,
    build_dvc,
    build_export,
    build_kfold,
    build_sagemaker,
    build_sahi,
    build_seg_isolation,
    build_tuning,
    build_validation,
)


class IntegrationsLayoutMixin:
    def _on_state_changed(self, state: object) -> None:
        self._state = state
        self._rebuild_ui()

    def _rebuild_ui(self) -> None:
        layout = self._root_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                continue
            l = item.layout()
            if l is not None:
                while l.count():
                    i2 = l.takeAt(0)
                    w2 = i2.widget()
                    if w2 is not None:
                        w2.setParent(None)
        self._build_ui()

    def _build_ui(self) -> None:
        t = Tokens
        layout = self._root_layout
        layout.setContentsMargins(t.space_lg, t.space_lg, t.space_lg, t.space_lg)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        content = QWidget()
        main = QVBoxLayout(content)
        main.setSpacing(t.space_lg)

        top = QHBoxLayout()
        top.addWidget(QLabel("Интеграции и мониторинг"))
        top.addStretch()
        export_btn = SecondaryButton("Экспорт конфигурации…")
        export_btn.clicked.connect(self._export_config)
        top.addWidget(export_btn)
        import_btn = SecondaryButton("Импорт конфигурации…")
        import_btn.clicked.connect(self._import_config)
        top.addWidget(import_btn)
        self._btn_cancel_job = SecondaryButton("Отменить задачу")
        self._btn_cancel_job.setEnabled(False)
        self._btn_cancel_job.clicked.connect(self._cancel_current_job)
        top.addWidget(self._btn_cancel_job)
        main.addLayout(top)

        self._job_status = QLabel("")
        self._job_status.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px;")
        main.addWidget(self._job_status)
        self._job_log = QTextEdit()
        self._job_log.setReadOnly(True)
        self._job_log.setMinimumHeight(120)
        self._job_log.setPlaceholderText("Логи фоновой задачи появятся здесь…")
        self._job_log.setStyleSheet(
            f"background: {t.surface}; color: {t.text_primary}; border: 1px solid {t.border}; border-radius: {t.radius_sm}px; padding: 6px; font-family: monospace; font-size: 11px;"
        )
        main.addWidget(self._job_log)

        cfg_label = QLabel(f"Файл конфигурации: {INTEGRATIONS_CONFIG_PATH}")
        cfg_label.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px;")
        main.addWidget(cfg_label)

        ctx = SectionsCtx(
            parent=self,
            vm=self._vm,
            state=self._state,
            toast_ok=self._toast_ok,
            toast_err=self._toast_err,
        )
        for builder in (
            build_comet,
            build_dvc,
            build_sagemaker,
            build_kfold,
            build_tuning,
            build_export,
            build_sahi,
            build_seg_isolation,
            build_validation,
        ):
            main.addWidget(builder(ctx))
        main.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
