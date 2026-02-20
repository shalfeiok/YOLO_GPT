"""
UI for model validation (model.val) and metrics (IoU, mAP).

Ref: https://docs.ultralytics.com/ru/guides/model-evaluation-insights/
"""

from __future__ import annotations

from threading import Thread
from tkinter import messagebox

import customtkinter as ctk

from app.features.model_validation.domain import ModelValidationConfig
from app.features.model_validation.repository import load_validation_config, save_validation_config
from app.features.model_validation.service import run_validation

DOC_URL = "https://docs.ultralytics.com/ru/guides/model-evaluation-insights/"


def build_validation_section(parent: ctk.CTkFrame) -> ctk.CTkFrame:
    sec = ctk.CTkFrame(parent, fg_color=("gray92", "gray24"), corner_radius=8, border_width=1)
    sec.grid_columnconfigure(1, weight=1)
    cfg = load_validation_config()
    row = 0

    ctk.CTkLabel(sec, text="K. Валидация модели (IoU, mAP)", font=ctk.CTkFont(weight="bold", size=14)).grid(
        row=row, column=0, columnspan=3, padx=12, pady=(12, 6), sticky="w"
    )
    row += 1
    ctk.CTkLabel(
        sec,
        text="Запуск model.val(data=...): mAP@.5, mAP@.5:.95, точность, полнота (recall).",
        wraplength=700,
        anchor="w",
        font=ctk.CTkFont(size=11),
    ).grid(row=row, column=0, columnspan=3, padx=12, pady=(0, 8), sticky="w")
    row += 1

    def open_doc() -> None:
        import webbrowser
        webbrowser.open(DOC_URL)

    ctk.CTkButton(sec, text="ℹ️ Подробнее", width=120, fg_color=("gray75", "gray35"), command=open_doc).grid(
        row=row, column=0, padx=12, pady=(0, 8), sticky="w"
    )
    row += 1

    ctk.CTkLabel(sec, text="data.yaml:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    data_e = ctk.CTkEntry(sec, width=380)
    data_e.insert(0, cfg.data_yaml)
    data_e.grid(row=row, column=1, padx=8, pady=4, sticky="ew")

    def browse_data() -> None:
        p = ctk.filedialog.askopenfilename(title="data.yaml", filetypes=[("YAML", "*.yaml"), ("Все", "*.*")])
        if p:
            data_e.delete(0, "end")
            data_e.insert(0, p)
            c = load_validation_config()
            c.data_yaml = p
            save_validation_config(c)

    ctk.CTkButton(sec, text="Обзор…", width=80, command=browse_data).grid(row=row, column=2, padx=4, pady=4)
    row += 1

    ctk.CTkLabel(sec, text="Веса (.pt):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    weights_e = ctk.CTkEntry(sec, width=380, placeholder_text="yolo11n.pt")
    weights_e.insert(0, cfg.weights_path)
    weights_e.grid(row=row, column=1, padx=8, pady=4, sticky="ew")

    def browse_weights() -> None:
        p = ctk.filedialog.askopenfilename(title="Веса", filetypes=[("PyTorch", "*.pt"), ("Все", "*.*")])
        if p:
            weights_e.delete(0, "end")
            weights_e.insert(0, p)
            c = load_validation_config()
            c.weights_path = p
            save_validation_config(c)

    ctk.CTkButton(sec, text="Обзор…", width=80, command=browse_weights).grid(row=row, column=2, padx=4, pady=4)
    row += 1

    prog_l = ctk.CTkLabel(sec, text="", font=ctk.CTkFont(size=10), text_color=("gray40", "gray55"))
    prog_l.grid(row=row, column=0, columnspan=3, padx=12, pady=4, sticky="w")
    row += 1

    def save_ui() -> None:
        c = load_validation_config()
        c.data_yaml = data_e.get().strip()
        c.weights_path = weights_e.get().strip()
        save_validation_config(c)

    def run() -> None:
        save_ui()
        cfg2 = load_validation_config()
        if not cfg2.data_yaml:
            messagebox.showwarning("Валидация", "Укажите data.yaml.")
            return

        def do() -> None:
            try:
                def prog(msg: str) -> None:
                    prog_l.configure(text=msg)
                    sec.update_idletasks()

                metrics = run_validation(cfg2, on_progress=prog)
                lines = ["Метрики валидации:"] + [f"  {k}: {v:.4f}" for k, v in sorted(metrics.items())]
                prog_l.configure(text="Готово.")
                messagebox.showinfo("Валидация", "\n".join(lines) if lines else "Готово.")
            except Exception as e:
                prog_l.configure(text="")
                messagebox.showerror("Валидация", str(e))

        Thread(target=do, daemon=True).start()

    ctk.CTkButton(sec, text="Запустить валидацию", width=180, command=run).grid(row=row, column=0, padx=12, pady=8, sticky="w")
    return sec
