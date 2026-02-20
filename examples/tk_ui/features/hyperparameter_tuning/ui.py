"""
UI section for Hyperparameter Tuning (model.tune).

Ref: https://docs.ultralytics.com/ru/guides/hyperparameter-tuning/
"""

from __future__ import annotations

from pathlib import Path
from threading import Thread
from tkinter import messagebox

import customtkinter as ctk

from app.features.hyperparameter_tuning.domain import TuningConfig
from app.features.hyperparameter_tuning.repository import load_tuning_config, save_tuning_config
from app.features.hyperparameter_tuning.service import run_tune

DOC_URL = "https://docs.ultralytics.com/ru/guides/hyperparameter-tuning/"


def build_tuning_section(parent: ctk.CTkFrame) -> ctk.CTkFrame:
    sec = ctk.CTkFrame(parent, fg_color=("gray92", "gray24"), corner_radius=8, border_width=1)
    sec.grid_columnconfigure(1, weight=1)

    cfg = load_tuning_config()
    row = 0

    ctk.CTkLabel(
        sec,
        text="G. Настройка гиперпараметров (model.tune)",
        font=ctk.CTkFont(weight="bold", size=14),
    ).grid(row=row, column=0, columnspan=3, padx=12, pady=(12, 6), sticky="w")
    row += 1
    ctk.CTkLabel(
        sec,
        text="Генетический поиск по гиперпараметрам YOLO (lr0, augmentation и др.). Результаты: best_hyperparameters.yaml, tune_results.csv в runs/detect/tune.",
        wraplength=700,
        anchor="w",
        justify="left",
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
    data_entry = ctk.CTkEntry(sec, width=400)
    data_entry.insert(0, cfg.data_yaml)
    data_entry.grid(row=row, column=1, padx=8, pady=4, sticky="ew")

    def browse_data() -> None:
        p = ctk.filedialog.askopenfilename(title="data.yaml", filetypes=[("YAML", "*.yaml"), ("Все", "*.*")])
        if p:
            data_entry.delete(0, "end")
            data_entry.insert(0, p)
            c = load_tuning_config()
            c.data_yaml = p
            save_tuning_config(c)

    ctk.CTkButton(sec, text="Обзор…", width=80, command=browse_data).grid(row=row, column=2, padx=4, pady=4)
    row += 1

    ctk.CTkLabel(sec, text="Модель (yolo11n.pt или .pt):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    model_entry = ctk.CTkEntry(sec, width=400, placeholder_text="yolo11n.pt")
    model_entry.insert(0, cfg.model_path)
    model_entry.grid(row=row, column=1, padx=8, pady=4, sticky="ew")

    def browse_model() -> None:
        p = ctk.filedialog.askopenfilename(title="Веса модели", filetypes=[("PyTorch", "*.pt"), ("Все", "*.*")])
        if p:
            model_entry.delete(0, "end")
            model_entry.insert(0, p)
            c = load_tuning_config()
            c.model_path = p
            save_tuning_config(c)

    ctk.CTkButton(sec, text="Обзор…", width=80, command=browse_model).grid(row=row, column=2, padx=4, pady=4)
    row += 1

    ctk.CTkLabel(sec, text="Эпохи:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    epochs_var = ctk.IntVar(value=cfg.epochs)
    ctk.CTkEntry(sec, width=80, textvariable=epochs_var).grid(row=row, column=1, padx=8, pady=4, sticky="w")
    row += 1

    ctk.CTkLabel(sec, text="Итерации настройки:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    iter_var = ctk.IntVar(value=cfg.iterations)
    ctk.CTkEntry(sec, width=80, textvariable=iter_var).grid(row=row, column=1, padx=8, pady=4, sticky="w")
    row += 1

    progress_label = ctk.CTkLabel(sec, text="", font=ctk.CTkFont(size=10), text_color=("gray40", "gray55"))
    progress_label.grid(row=row, column=0, columnspan=3, padx=12, pady=4, sticky="w")
    row += 1

    def save_ui() -> None:
        c = load_tuning_config()
        c.data_yaml = data_entry.get().strip()
        c.model_path = model_entry.get().strip()
        c.epochs = max(1, epochs_var.get())
        c.iterations = max(1, iter_var.get())
        save_tuning_config(c)

    def start_tune() -> None:
        save_ui()
        cfg2 = load_tuning_config()
        if not cfg2.data_yaml:
            messagebox.showwarning("Настройка", "Укажите data.yaml.")
            return

        def do() -> None:
            try:
                def prog(msg: str) -> None:
                    progress_label.configure(text=msg)
                    sec.update_idletasks()

                run_tune(cfg2, on_progress=prog)
                progress_label.configure(text="Готово. См. runs/detect/tune.")
                messagebox.showinfo("Настройка", "Настройка гиперпараметров завершена. Результаты в runs/detect/tune.")
            except Exception as e:
                progress_label.configure(text="")
                messagebox.showerror("Настройка", str(e))

        Thread(target=do, daemon=True).start()

    ctk.CTkButton(sec, text="Запустить настройку гиперпараметров", width=260, command=start_tune).grid(
        row=row, column=0, padx=12, pady=8, sticky="w"
    )
    return sec
