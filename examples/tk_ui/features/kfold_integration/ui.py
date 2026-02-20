"""
UI section for K-Fold Cross Validation: paths, K, Generate folds, optional Train all folds.

Ref: https://docs.ultralytics.com/ru/guides/kfold-cross-validation/
"""

from __future__ import annotations

import datetime
from pathlib import Path
from queue import Queue
from threading import Thread
from tkinter import messagebox

import customtkinter as ctk

from app.features.kfold_integration.domain import KFoldConfig
from app.features.kfold_integration.repository import load_kfold_config, save_kfold_config
from app.features.kfold_integration.service import run_kfold_split, run_kfold_train

DOC_URL = "https://docs.ultralytics.com/ru/guides/kfold-cross-validation/"


def build_kfold_section(
    parent: ctk.CTkFrame,
    on_reset_defaults: None = None,
    console_queue: Queue | None = None,
) -> ctk.CTkFrame:
    """Build K-Fold Cross Validation section (Generate folds, optional Train all folds)."""
    sec = ctk.CTkFrame(parent, fg_color=("gray92", "gray24"), corner_radius=8, border_width=1)
    sec.grid_columnconfigure(1, weight=1)

    cfg = load_kfold_config()
    row = 0

    ctk.CTkLabel(
        sec,
        text="F. K-Fold перекрёстная проверка",
        font=ctk.CTkFont(weight="bold", size=14),
    ).grid(row=row, column=0, columnspan=3, padx=12, pady=(12, 6), sticky="w")
    row += 1
    desc = ctk.CTkLabel(
        sec,
        text="Разбейте набор данных на K фолдов (train/val), создайте data.yaml для каждого и при необходимости запустите обучение по каждому фолду. Требуются: sklearn, pandas, pyyaml.",
        wraplength=700,
        anchor="w",
        justify="left",
        font=ctk.CTkFont(size=11),
    )
    desc.grid(row=row, column=0, columnspan=3, padx=12, pady=(0, 8), sticky="w")
    row += 1

    def open_doc() -> None:
        import webbrowser
        webbrowser.open(DOC_URL)

    ctk.CTkButton(sec, text="ℹ️ Подробнее", width=120, fg_color=("gray75", "gray35"), command=open_doc).grid(
        row=row, column=0, padx=12, pady=(0, 8), sticky="w"
    )
    row += 1

    # Dataset path
    ctk.CTkLabel(sec, text="Путь к датасету (папка с images/ и labels/):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    ds_entry = ctk.CTkEntry(sec, width=400, placeholder_text="C:\\data\\Fruit-Detection")
    ds_entry.insert(0, cfg.dataset_path)
    ds_entry.grid(row=row, column=1, columnspan=2, padx=8, pady=4, sticky="ew")

    def browse_dataset() -> None:
        p = ctk.filedialog.askdirectory(title="Выберите папку датасета")
        if p:
            ds_entry.delete(0, "end")
            ds_entry.insert(0, p)
            c = load_kfold_config()
            c.dataset_path = p
            save_kfold_config(c)

    ctk.CTkButton(sec, text="Обзор…", width=80, command=browse_dataset).grid(row=row, column=2, padx=4, pady=4)
    row += 1

    # Data YAML
    ctk.CTkLabel(sec, text="data.yaml (пути и имена классов):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    yaml_entry = ctk.CTkEntry(sec, width=400, placeholder_text="path/to/data.yaml")
    yaml_entry.insert(0, cfg.data_yaml_path)
    yaml_entry.grid(row=row, column=1, columnspan=2, padx=8, pady=4, sticky="ew")

    def browse_yaml() -> None:
        p = ctk.filedialog.askopenfilename(title="Выберите data.yaml", filetypes=[("YAML", "*.yaml"), ("Все", "*.*")])
        if p:
            yaml_entry.delete(0, "end")
            yaml_entry.insert(0, p)
            c = load_kfold_config()
            c.data_yaml_path = p
            save_kfold_config(c)
    ctk.CTkButton(sec, text="Обзор…", width=80, command=browse_yaml).grid(row=row, column=2, padx=4, pady=4)
    row += 1

    # K folds
    ctk.CTkLabel(sec, text="Число фолдов K:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    k_var = ctk.IntVar(value=cfg.k_folds)
    k_spin = ctk.CTkEntry(sec, width=80, textvariable=k_var)
    k_spin.grid(row=row, column=1, padx=8, pady=4, sticky="w")
    row += 1

    # Output path (optional)
    ctk.CTkLabel(sec, text="Папка для фолдов (пусто = рядом с датасетом):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    out_entry = ctk.CTkEntry(sec, width=400, placeholder_text="Оставьте пустым для авто")
    out_entry.insert(0, cfg.output_path)
    out_entry.grid(row=row, column=1, columnspan=2, padx=8, pady=4, sticky="ew")
    row += 1

    # Progress label
    progress_label = ctk.CTkLabel(sec, text="", font=ctk.CTkFont(size=10), text_color=("gray40", "gray55"))
    progress_label.grid(row=row, column=0, columnspan=3, padx=12, pady=4, sticky="w")
    row += 1

    def save_from_ui() -> None:
        c = load_kfold_config()
        c.dataset_path = ds_entry.get().strip()
        c.data_yaml_path = yaml_entry.get().strip()
        c.k_folds = max(2, min(20, k_var.get()))
        c.output_path = out_entry.get().strip()
        save_kfold_config(c)

    def run_split() -> None:
        save_from_ui()
        cfg2 = load_kfold_config()
        if not cfg2.dataset_path or not cfg2.data_yaml_path:
            messagebox.showwarning("K-Fold", "Укажите путь к датасету и data.yaml.")
            return

        def do() -> None:
            try:
                def prog(msg: str) -> None:
                    progress_label.configure(text=msg)
                    sec.update_idletasks()

                ds_yamls = run_kfold_split(cfg2, on_progress=prog)
                used_path = Path(cfg2.output_path) if cfg2.output_path else Path(cfg2.dataset_path) / f"{datetime.date.today().isoformat()}_{cfg2.k_folds}-Fold_Cross-val"
                cfg2.output_path = str(used_path)
                save_kfold_config(cfg2)
                def update_ui() -> None:
                    out_entry.delete(0, "end")
                    out_entry.insert(0, str(used_path))
                sec.after(0, update_ui)
                progress_label.configure(text=f"Готово. Создано {len(ds_yamls)} фолдов.")
                messagebox.showinfo("K-Fold", f"Разбиение сохранено. Dataset YAML: {len(ds_yamls)} файлов.")
            except Exception as e:
                progress_label.configure(text="")
                messagebox.showerror("K-Fold", str(e))

        progress_label.configure(text="Выполняется разбиение…")
        Thread(target=do, daemon=True).start()

    ctk.CTkButton(sec, text="Сгенерировать фолды", width=180, command=run_split).grid(row=row, column=0, padx=12, pady=8, sticky="w")
    row += 1

    # Optional: weights and "Train all folds"
    ctk.CTkLabel(sec, text="Веса для обучения по фолдам (опционально):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    weights_entry = ctk.CTkEntry(sec, width=400, placeholder_text="yolo11n.pt или путь к .pt")
    weights_entry.insert(0, cfg.weights_path)
    weights_entry.grid(row=row, column=1, columnspan=2, padx=8, pady=4, sticky="ew")

    def save_weights() -> None:
        c = load_kfold_config()
        c.weights_path = weights_entry.get().strip()
        save_kfold_config(c)
    weights_entry.bind("<FocusOut>", lambda e: save_weights())
    row += 1

    def run_train_all() -> None:
        save_from_ui()
        cfg2 = load_kfold_config()
        if not cfg2.dataset_path:
            messagebox.showwarning("K-Fold", "Укажите путь к датасету.")
            return
        k = max(2, min(20, k_var.get()))
        # Используем сохранённый output_path (заполняется после «Сгенерировать фолды») или авто-путь
        save_path = Path(cfg2.output_path) if cfg2.output_path else Path(cfg2.dataset_path) / f"{datetime.date.today().isoformat()}_{k}-Fold_Cross-val"
        ds_yamls = [save_path / f"split_{i}" / f"split_{i}_dataset.yaml" for i in range(1, k + 1)]
        if not ds_yamls or not all(p.exists() for p in ds_yamls):
            messagebox.showwarning("K-Fold", "Сначала нажмите «Сгенерировать фолды». Не найдены YAML фолдов в:\n" + str(save_path))
            return

        def do() -> None:
            try:
                def prog(msg: str) -> None:
                    progress_label.configure(text=msg)
                    sec.update_idletasks()

                run_kfold_train(cfg2, ds_yamls, on_progress=prog)
                progress_label.configure(text="Обучение по фолдам завершено.")
                messagebox.showinfo("K-Fold", "Обучение по всем фолдам завершено. См. runs/detect или указанный project.")
            except Exception as e:
                progress_label.configure(text="")
                messagebox.showerror("K-Fold", str(e))

        progress_label.configure(text="Обучение по фолдам…")
        Thread(target=do, daemon=True).start()

    ctk.CTkButton(sec, text="Обучить все фолды", width=180, fg_color=("gray65", "gray28"), command=run_train_all).grid(
        row=row, column=0, padx=12, pady=8, sticky="w"
    )
    row += 1

    return sec


def _build_kfold_section_with_train(
    parent: ctk.CTkFrame,
    console_queue: Queue | None = None,
) -> ctk.CTkFrame:
    """Variant that includes 'Train all folds' button; use last generated output dir."""
    # Re-use build_kfold_section and add train button in integrations_tab by placing section + extra row
    return build_kfold_section(parent, console_queue=console_queue)
