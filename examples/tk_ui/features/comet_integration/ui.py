"""
UI section for Comet ML: enable, API key, project name, advanced settings, open panel.

Ref: https://docs.ultralytics.com/ru/integrations/comet/
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.features.comet_integration.domain import CometConfig
from app.features.comet_integration.repository import load_comet_config, save_comet_config

DESCRIPTION = (
    "Comet ML — платформа для сравнения экспериментов, визуализации метрик и управления моделями. "
    "Автоматически логирует mAP, loss, гиперпараметры, матрицу ошибок и примеры предсказаний."
)
DOC_URL = "https://docs.ultralytics.com/ru/integrations/comet/"


def build_comet_section(
    parent: ctk.CTkFrame,
    on_reset_defaults: Callable[[], None] | None = None,
) -> ctk.CTkFrame:
    sec = ctk.CTkFrame(parent, fg_color=("gray92", "gray24"), corner_radius=8, border_width=1)
    sec.grid_columnconfigure(1, weight=1)
    cfg = load_comet_config()
    row = 0

    ctk.CTkLabel(
        sec,
        text="B. Трекинг экспериментов (Comet ML)",
        font=ctk.CTkFont(weight="bold", size=14),
    ).grid(row=row, column=0, columnspan=3, padx=12, pady=(12, 6), sticky="w")
    row += 1
    ctk.CTkLabel(sec, text=DESCRIPTION, wraplength=700, anchor="w", justify="left", font=ctk.CTkFont(size=11)).grid(
        row=row, column=0, columnspan=3, padx=12, pady=(0, 8), sticky="w"
    )
    row += 1

    def open_doc() -> None:
        import webbrowser
        webbrowser.open(DOC_URL)

    ctk.CTkButton(sec, text="ℹ️ Подробнее", width=120, fg_color=("gray75", "gray35"), command=open_doc).grid(
        row=row, column=0, padx=12, pady=(0, 8), sticky="w"
    )
    row += 1

    enabled_var = ctk.BooleanVar(value=cfg.enabled)

    def save_enabled() -> None:
        c = load_comet_config()
        c.enabled = enabled_var.get()
        save_comet_config(c)

    ctk.CTkCheckBox(sec, text="Логировать эксперименты в Comet ML", variable=enabled_var, command=save_enabled).grid(
        row=row, column=0, columnspan=2, padx=12, pady=4, sticky="w"
    )
    row += 1

    ctk.CTkLabel(sec, text="Comet API Key:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    api_var = ctk.StringVar(value=cfg.api_key)
    api_entry = ctk.CTkEntry(sec, textvariable=api_var, width=280, show="*")
    api_entry.grid(row=row, column=1, padx=0, pady=4, sticky="ew")

    def save_api(*args: object) -> None:
        c = load_comet_config()
        c.api_key = api_var.get().strip()
        save_comet_config(c)

    api_var.trace_add("write", save_api)
    row += 1

    ctk.CTkLabel(sec, text="Project Name:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    project_var = ctk.StringVar(value=cfg.project_name)
    ctk.CTkEntry(sec, textvariable=project_var, width=280).grid(row=row, column=1, padx=0, pady=4, sticky="ew")

    def save_project(*args: object) -> None:
        c = load_comet_config()
        c.project_name = project_var.get().strip()
        save_comet_config(c)

    project_var.trace_add("write", save_project)
    row += 1

    # Collapsible advanced
    advanced_frame = ctk.CTkFrame(sec, fg_color="transparent")
    advanced_frame.grid(row=row, column=0, columnspan=3, sticky="ew", padx=12, pady=4)
    advanced_frame.grid_columnconfigure(1, weight=1)
    ar = 0
    ctk.CTkLabel(advanced_frame, text="Дополнительные настройки:", font=ctk.CTkFont(weight="bold")).grid(
        row=ar, column=0, columnspan=2, padx=0, pady=4, sticky="w"
    )
    ar += 1
    ctk.CTkLabel(advanced_frame, text="COMET_MAX_IMAGE_PREDICTIONS:").grid(row=ar, column=0, padx=0, pady=2, sticky="w")
    max_img_var = ctk.StringVar(value=str(cfg.max_image_predictions))
    ctk.CTkEntry(advanced_frame, textvariable=max_img_var, width=80).grid(row=ar, column=1, padx=8, pady=2, sticky="w")

    def save_adv(*args: object) -> None:
        c = load_comet_config()
        try:
            c.max_image_predictions = int(max_img_var.get())
        except ValueError:
            pass
        try:
            c.eval_batch_logging_interval = int(eval_interval_var.get())
        except ValueError:
            pass
        c.eval_log_confusion_matrix = eval_cm_var.get()
        c.mode = mode_var.get()
        save_comet_config(c)

    max_img_var.trace_add("write", save_adv)
    ar += 1
    ctk.CTkLabel(advanced_frame, text="COMET_EVAL_BATCH_LOGGING_INTERVAL:").grid(row=ar, column=0, padx=0, pady=2, sticky="w")
    eval_interval_var = ctk.StringVar(value=str(cfg.eval_batch_logging_interval))
    ctk.CTkEntry(advanced_frame, textvariable=eval_interval_var, width=80).grid(row=ar, column=1, padx=8, pady=2, sticky="w")
    eval_interval_var.trace_add("write", save_adv)
    ar += 1
    eval_cm_var = ctk.BooleanVar(value=cfg.eval_log_confusion_matrix)
    ctk.CTkCheckBox(advanced_frame, text="COMET_EVAL_LOG_CONFUSION_MATRIX", variable=eval_cm_var, command=save_adv).grid(
        row=ar, column=0, columnspan=2, padx=0, pady=2, sticky="w"
    )
    ar += 1
    ctk.CTkLabel(advanced_frame, text="COMET_MODE:").grid(row=ar, column=0, padx=0, pady=2, sticky="w")
    mode_var = ctk.StringVar(value=cfg.mode)
    ctk.CTkOptionMenu(advanced_frame, variable=mode_var, values=["online", "offline", "disabled"], width=120, command=lambda _: save_adv()).grid(
        row=ar, column=1, padx=8, pady=2, sticky="w"
    )
    row += 1

    def open_comet_panel() -> None:
        import webbrowser
        webbrowser.open("https://www.comet.com/site/")

    ctk.CTkButton(sec, text="Открыть панель Comet в браузере", width=220, command=open_comet_panel).grid(
        row=row, column=0, columnspan=2, padx=12, pady=8, sticky="w"
    )
    row += 1

    if on_reset_defaults:

        def reset() -> None:
            default = CometConfig(
                enabled=False,
                api_key="",
                project_name="yolo26-project",
                max_image_predictions=100,
                eval_batch_logging_interval=1,
                eval_log_confusion_matrix=True,
                mode="online",
            )
            save_comet_config(default)
            enabled_var.set(default.enabled)
            api_var.set(default.api_key)
            project_var.set(default.project_name)
            max_img_var.set(str(default.max_image_predictions))
            eval_interval_var.set(str(default.eval_batch_logging_interval))
            eval_cm_var.set(default.eval_log_confusion_matrix)
            mode_var.set(default.mode)
            if on_reset_defaults:
                on_reset_defaults()

        ctk.CTkButton(sec, text="Сбросить настройки по умолчанию", width=220, fg_color=("gray70", "gray30"), command=reset).grid(
            row=row, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="w"
        )

    return sec
