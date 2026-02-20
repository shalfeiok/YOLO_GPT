"""
UI section for SageMaker: warning, clone template, params, deploy via CDK (async), clear endpoint.

Ref: https://docs.ultralytics.com/ru/integrations/amazon-sagemaker/
"""

from __future__ import annotations

from pathlib import Path
from queue import Queue
from threading import Thread
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from app.config import PROJECT_ROOT
from app.features.sagemaker_integration.domain import SageMakerConfig
from app.features.sagemaker_integration.repository import load_sagemaker_config, save_sagemaker_config
from app.features.sagemaker_integration.service import clone_sagemaker_template, run_cdk_deploy

DESCRIPTION = (
    "Amazon SageMaker — управляемый сервис для масштабируемого инференса. "
    "Развёртывание через AWS CDK обеспечивает воспроизводимую инфраструктуру."
)
DOC_URL = "https://docs.ultralytics.com/ru/integrations/amazon-sagemaker/"


def build_sagemaker_section(
    parent: ctk.CTkFrame,
    on_reset_defaults: Callable[[], None] | None = None,
) -> ctk.CTkFrame:
    sec = ctk.CTkFrame(parent, fg_color=("gray92", "gray24"), corner_radius=8, border_width=1)
    sec.grid_columnconfigure(1, weight=1)
    cfg = load_sagemaker_config()
    row = 0

    ctk.CTkLabel(
        sec,
        text="D. Облачный деплой (Amazon SageMaker)",
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

    warn = ctk.CTkLabel(
        sec,
        text="⚠ Требуется настроенный AWS CLI и права на создание ресурсов.",
        text_color=("orange", "orange"),
        font=ctk.CTkFont(weight="bold"),
    )
    warn.grid(row=row, column=0, columnspan=3, padx=12, pady=4, sticky="w")
    row += 1

    def do_clone() -> None:
        ok, path_or_err = clone_sagemaker_template(PROJECT_ROOT)
        if ok:
            c = load_sagemaker_config()
            c.template_cloned_path = path_or_err
            save_sagemaker_config(c)
            template_var.set(path_or_err)
            try:
                from tkinter import messagebox
                messagebox.showinfo("SageMaker", f"Шаблон склонирован: {path_or_err}")
            except Exception:
                import logging
                logging.getLogger(__name__).debug('Optional example integration failed', exc_info=True)
        else:
            try:
                from tkinter import messagebox
                messagebox.showerror("SageMaker", path_or_err)
            except Exception:
                import logging
                logging.getLogger(__name__).debug('Optional example integration failed', exc_info=True)
    ctk.CTkButton(sec, text="Клонировать шаблон SageMaker", width=220, command=do_clone).grid(
        row=row, column=0, columnspan=2, padx=12, pady=4, sticky="w"
    )
    row += 1

    ctk.CTkLabel(sec, text="Путь к шаблону:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    template_var = ctk.StringVar(value=cfg.template_cloned_path)
    ctk.CTkEntry(sec, textvariable=template_var, width=350).grid(row=row, column=1, padx=0, pady=4, sticky="ew")

    def save_template(*args: object) -> None:
        c = load_sagemaker_config()
        c.template_cloned_path = template_var.get().strip()
        save_sagemaker_config(c)

    template_var.trace_add("write", save_template)
    row += 1

    ctk.CTkLabel(sec, text="Instance type:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    instance_var = ctk.StringVar(value=cfg.instance_type)
    ctk.CTkOptionMenu(
        sec,
        variable=instance_var,
        values=["ml.m5.4xlarge", "ml.m5.2xlarge", "ml.g4dn.xlarge", "ml.c5.2xlarge"],
        width=180,
        command=lambda _: _save_instance(),
    ).grid(row=row, column=1, padx=0, pady=4, sticky="w")

    def _save_instance() -> None:
        c = load_sagemaker_config()
        c.instance_type = instance_var.get()
        save_sagemaker_config(c)

    row += 1

    ctk.CTkLabel(sec, text="Название endpoint:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    endpoint_var = ctk.StringVar(value=cfg.endpoint_name)
    ctk.CTkEntry(sec, textvariable=endpoint_var, width=250).grid(row=row, column=1, padx=0, pady=4, sticky="ew")
    endpoint_var.trace_add("write", lambda *a: _save_endpoint())
    row += 1

    def _save_endpoint() -> None:
        c = load_sagemaker_config()
        c.endpoint_name = endpoint_var.get().strip()
        save_sagemaker_config(c)

    ctk.CTkLabel(sec, text="Путь к модели (.pt):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    model_var = ctk.StringVar(value=cfg.model_path)
    ctk.CTkEntry(sec, textvariable=model_var, width=300).grid(row=row, column=1, padx=0, pady=4, sticky="ew")
    ctk.CTkButton(sec, text="Обзор…", width=80, command=lambda: _browse_model()).grid(row=row, column=2, padx=(8, 0), pady=4)

    def _browse_model() -> None:
        path = filedialog.askopenfilename(
            title="Выберите веса (.pt)",
            initialdir=PROJECT_ROOT,
            filetypes=[("PyTorch", "*.pt"), ("Все файлы", "*.*")],
        )
        if path:
            model_var.set(path)

    def _save_model(*args: object) -> None:
        c = load_sagemaker_config()
        c.model_path = model_var.get().strip()
        save_sagemaker_config(c)

    model_var.trace_add("write", _save_model)
    row += 1

    deploy_log = ctk.CTkTextbox(sec, height=120, font=ctk.CTkFont(size=10))
    deploy_log.grid(row=row, column=0, columnspan=3, sticky="ew", padx=12, pady=4)
    sec.grid_rowconfigure(row, minsize=120)
    row += 1

    deploy_status_var = ctk.StringVar(value="")

    def do_deploy() -> None:
        tp = template_var.get().strip()
        if not tp or not Path(tp).is_dir():
            try:
                from tkinter import messagebox
                messagebox.showerror("SageMaker", "Укажите путь к склонированному шаблону.")
            except Exception:
                import logging
                logging.getLogger(__name__).debug('Optional example integration failed', exc_info=True)
            return
        queue: Queue = Queue()

        def run() -> None:
            ok, msg = run_cdk_deploy(Path(tp), on_output=lambda s: queue.put(("log", s)))
            queue.put(("done", (ok, msg)))

        def poll() -> None:
            try:
                while True:
                    kind, payload = queue.get_nowait()
                    if kind == "log":
                        deploy_log.insert("end", payload)
                        deploy_log.see("end")
                    elif kind == "done":
                        ok, msg = payload
                        deploy_status_var.set(msg)
                        deploy_btn.configure(state="normal")
                        return
            except Exception:
                import logging
                logging.getLogger(__name__).debug('Optional example integration failed', exc_info=True)
            sec.after(100, poll)

        deploy_log.delete("1.0", "end")
        deploy_status_var.set("Развёртывание…")
        deploy_btn.configure(state="disabled")
        Thread(target=run, daemon=True).start()
        sec.after(100, poll)

    deploy_btn = ctk.CTkButton(sec, text="Развернуть через CDK", width=180, command=do_deploy)
    deploy_btn.grid(row=row, column=0, columnspan=2, padx=12, pady=4, sticky="w")
    row += 1
    ctk.CTkLabel(sec, textvariable=deploy_status_var, wraplength=400).grid(row=row, column=0, columnspan=2, padx=12, pady=4, sticky="w")
    row += 1

    def do_clear_endpoint() -> None:
        try:
            from tkinter import messagebox
            messagebox.showinfo("Очистка", "Очистку endpoint выполните в консоли AWS SageMaker или через CDK destroy.")
        except Exception:
            import logging
            logging.getLogger(__name__).debug('Optional example integration failed', exc_info=True)
    ctk.CTkButton(sec, text="Очистить endpoint", width=160, fg_color=("gray70", "gray30"), command=do_clear_endpoint).grid(
        row=row, column=0, padx=12, pady=4, sticky="w"
    )
    row += 1

    if on_reset_defaults:

        def reset() -> None:
            default = SageMakerConfig(
                instance_type="ml.m5.4xlarge",
                endpoint_name="",
                model_path="",
                template_cloned_path="",
            )
            save_sagemaker_config(default)
            instance_var.set(default.instance_type)
            endpoint_var.set(default.endpoint_name)
            model_var.set(default.model_path)
            template_var.set(default.template_cloned_path)
            if on_reset_defaults:
                on_reset_defaults()

        ctk.CTkButton(sec, text="Сбросить настройки по умолчанию", width=220, fg_color=("gray70", "gray30"), command=reset).grid(
            row=row, column=0, columnspan=2, padx=12, pady=(8, 12), sticky="w"
        )

    return sec
