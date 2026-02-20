"""
UI section for DVC: enable, git/dvc indicators, init DVC, generate DVC plots (async).

Ref: https://docs.ultralytics.com/ru/integrations/dvc/
"""

from __future__ import annotations

import webbrowser
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Callable

import customtkinter as ctk

from app.features.dvc_integration.domain import DVCConfig
from app.features.dvc_integration.repository import load_dvc_config, save_dvc_config
from app.features.dvc_integration.service import (
    get_current_branch,
    init_dvc_in_project,
    is_dvc_initialized,
    is_git_repo,
    run_dvc_plots_diff,
)

DESCRIPTION = (
    "DVCLive + DVC обеспечивают версионирование данных и метрик, интеграцию с Git и генерацию сравнительных отчётов. "
    "Позволяет отследить, какая версия кода и данных дала лучший результат."
)
DOC_URL = "https://docs.ultralytics.com/ru/integrations/dvc/"


def build_dvc_section(
    parent: ctk.CTkFrame,
    on_reset_defaults: Callable[[], None] | None = None,
) -> ctk.CTkFrame:
    sec = ctk.CTkFrame(parent, fg_color=("gray92", "gray24"), corner_radius=8, border_width=1)
    sec.grid_columnconfigure(1, weight=1)
    cfg = load_dvc_config()
    row = 0

    ctk.CTkLabel(
        sec,
        text="C. Версионирование экспериментов (DVCLive)",
        font=ctk.CTkFont(weight="bold", size=14),
    ).grid(row=row, column=0, columnspan=3, padx=12, pady=(12, 6), sticky="w")
    row += 1
    ctk.CTkLabel(sec, text=DESCRIPTION, wraplength=700, anchor="w", justify="left", font=ctk.CTkFont(size=11)).grid(
        row=row, column=0, columnspan=3, padx=12, pady=(0, 8), sticky="w"
    )
    row += 1

    def open_doc() -> None:
        webbrowser.open(DOC_URL)

    ctk.CTkButton(sec, text="ℹ️ Подробнее", width=120, fg_color=("gray75", "gray35"), command=open_doc).grid(
        row=row, column=0, padx=12, pady=(0, 8), sticky="w"
    )
    row += 1

    enabled_var = ctk.BooleanVar(value=cfg.enabled)

    def save_enabled() -> None:
        c = load_dvc_config()
        c.enabled = enabled_var.get()
        save_dvc_config(c)

    ctk.CTkCheckBox(sec, text="Отслеживать эксперименты с DVC", variable=enabled_var, command=save_enabled).grid(
        row=row, column=0, columnspan=2, padx=12, pady=4, sticky="w"
    )
    row += 1

    git_var = ctk.StringVar(value="Да" if is_git_repo() else "Нет")
    dvc_var = ctk.StringVar(value="Да" if is_dvc_initialized() else "Нет")
    branch_var = ctk.StringVar(value=get_current_branch() or "—")

    def refresh_indicators() -> None:
        git_var.set("Да" if is_git_repo() else "Нет")
        dvc_var.set("Да" if is_dvc_initialized() else "Нет")
        branch_var.set(get_current_branch() or "—")

    ctk.CTkLabel(sec, text="Git репозиторий инициализирован:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    ctk.CTkLabel(sec, textvariable=git_var).grid(row=row, column=1, padx=0, pady=4, sticky="w")
    row += 1
    ctk.CTkLabel(sec, text="DVC инициализирован:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    ctk.CTkLabel(sec, textvariable=dvc_var).grid(row=row, column=1, padx=0, pady=4, sticky="w")
    row += 1
    ctk.CTkLabel(sec, text="Текущая ветка Git:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    ctk.CTkLabel(sec, textvariable=branch_var).grid(row=row, column=1, padx=0, pady=4, sticky="w")
    row += 1

    def do_init_dvc() -> None:
        ok, msg = init_dvc_in_project()
        refresh_indicators()
        if ok:
            ctk.CTkLabel(sec, text=msg, text_color=("green", "lightgreen")).grid(
                row=row, column=0, columnspan=2, padx=12, pady=4, sticky="w"
            )
        else:
            # Show error in messagebox
            try:
                from tkinter import messagebox
                messagebox.showerror("DVC", msg)
            except Exception:
                import logging
                logging.getLogger(__name__).debug('Optional example integration failed', exc_info=True)
    ctk.CTkButton(sec, text="Инициализировать DVC в проекте", width=240, command=do_init_dvc).grid(
        row=row, column=0, columnspan=2, padx=12, pady=4, sticky="w"
    )
    row += 1

    status_var = ctk.StringVar(value="")
    log_text = ctk.CTkTextbox(sec, height=80, font=ctk.CTkFont(size=10))
    log_text.grid(row=row, column=0, columnspan=3, sticky="ew", padx=12, pady=4)
    sec.grid_rowconfigure(row, minsize=80)
    row += 1

    def do_plots() -> None:
        queue: Queue = Queue()

        def run() -> None:
            ok, result = run_dvc_plots_diff(on_output=lambda s: queue.put(("log", s)))
            queue.put(("done", (ok, result)))

        def poll() -> None:
            try:
                while True:
                    kind, payload = queue.get_nowait()
                    if kind == "log":
                        log_text.insert("end", payload)
                        log_text.see("end")
                    elif kind == "done":
                        ok, path_or_err = payload
                        if ok:
                            status_var.set(f"Готово: {path_or_err}")
                            p = Path(path_or_err)
                            if p.suffix == ".html":
                                webbrowser.open(f"file://{p.resolve()}")
                        else:
                            status_var.set(f"Ошибка: {path_or_err}")
                        plots_btn.configure(state="normal")
                        return
            except Exception:
                import logging
                logging.getLogger(__name__).debug('Optional example integration failed', exc_info=True)
            sec.after(100, poll)

        log_text.delete("1.0", "end")
        status_var.set("Генерация отчёта…")
        plots_btn.configure(state="disabled")
        Thread(target=run, daemon=True).start()
        sec.after(100, poll)

    plots_btn = ctk.CTkButton(
        sec,
        text="Сгенерировать отчёт DVC plots",
        width=220,
        command=do_plots,
    )
    plots_btn.grid(row=row, column=0, columnspan=2, padx=12, pady=4, sticky="w")
    row += 1
    ctk.CTkLabel(sec, textvariable=status_var, wraplength=400).grid(row=row, column=0, columnspan=2, padx=12, pady=4, sticky="w")
    row += 1

    if on_reset_defaults:

        def reset() -> None:
            default = DVCConfig(enabled=False)
            save_dvc_config(default)
            enabled_var.set(default.enabled)
            refresh_indicators()
            if on_reset_defaults:
                on_reset_defaults()

        ctk.CTkButton(sec, text="Сбросить настройки по умолчанию", width=220, fg_color=("gray70", "gray30"), command=reset).grid(
            row=row, column=0, columnspan=2, padx=12, pady=(8, 12), sticky="w"
        )

    return sec
