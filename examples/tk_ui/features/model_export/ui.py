"""
UI section for exporting YOLO model (ONNX, OpenVINO, TF, etc.).

Ref: https://docs.ultralytics.com/ru/guides/model-deployment-options/
"""

from __future__ import annotations

from pathlib import Path
from threading import Thread
from tkinter import messagebox

import customtkinter as ctk

from app.features.model_export.domain import ModelExportConfig, EXPORT_FORMATS
from app.features.model_export.repository import load_export_config, save_export_config
from app.features.model_export.service import run_export

DOC_URL = "https://docs.ultralytics.com/ru/guides/model-deployment-options/"


def build_export_section(parent: ctk.CTkFrame) -> ctk.CTkFrame:
    sec = ctk.CTkFrame(parent, fg_color=("gray92", "gray24"), corner_radius=8, border_width=1)
    sec.grid_columnconfigure(1, weight=1)

    cfg = load_export_config()
    row = 0

    ctk.CTkLabel(
        sec,
        text="H. Экспорт модели (ONNX, OpenVINO, TensorFlow, …)",
        font=ctk.CTkFont(weight="bold", size=14),
    ).grid(row=row, column=0, columnspan=3, padx=12, pady=(12, 6), sticky="w")
    row += 1
    ctk.CTkLabel(
        sec,
        text="Экспорт весов YOLO в формат для развёртывания: ONNX, OpenVINO, TensorFlow SavedModel/GraphDef, TFLite, TensorRT, CoreML и др.",
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

    ctk.CTkLabel(sec, text="Веса (.pt):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    weights_entry = ctk.CTkEntry(sec, width=400)
    weights_entry.insert(0, cfg.weights_path)
    weights_entry.grid(row=row, column=1, padx=8, pady=4, sticky="ew")

    def browse_weights() -> None:
        p = ctk.filedialog.askopenfilename(title="Веса модели", filetypes=[("PyTorch", "*.pt"), ("Все", "*.*")])
        if p:
            weights_entry.delete(0, "end")
            weights_entry.insert(0, p)
            c = load_export_config()
            c.weights_path = p
            save_export_config(c)

    ctk.CTkButton(sec, text="Обзор…", width=80, command=browse_weights).grid(row=row, column=2, padx=4, pady=4)
    row += 1

    ctk.CTkLabel(sec, text="Формат:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    format_var = ctk.StringVar(value=cfg.format if cfg.format in EXPORT_FORMATS else "onnx")
    ctk.CTkOptionMenu(sec, variable=format_var, values=EXPORT_FORMATS, width=180).grid(
        row=row, column=1, padx=8, pady=4, sticky="w"
    )
    row += 1

    progress_label = ctk.CTkLabel(sec, text="", font=ctk.CTkFont(size=10), text_color=("gray40", "gray55"))
    progress_label.grid(row=row, column=0, columnspan=3, padx=12, pady=4, sticky="w")
    row += 1

    def save_ui() -> None:
        c = load_export_config()
        c.weights_path = weights_entry.get().strip()
        c.format = format_var.get()
        save_export_config(c)

    def start_export() -> None:
        save_ui()
        cfg2 = load_export_config()
        if not cfg2.weights_path:
            messagebox.showwarning("Экспорт", "Укажите путь к весам (.pt).")
            return
        if not Path(cfg2.weights_path).exists() and not cfg2.weights_path.startswith("yolo"):
            messagebox.showwarning("Экспорт", "Файл весов не найден.")
            return

        def do() -> None:
            try:
                def prog(msg: str) -> None:
                    progress_label.configure(text=msg)
                    sec.update_idletasks()

                out = run_export(cfg2, on_progress=prog)
                progress_label.configure(text=f"Готово: {out}" if out else "Готово.")
                messagebox.showinfo("Экспорт", f"Экспорт завершён: {out}" if out else "Экспорт завершён.")
            except Exception as e:
                progress_label.configure(text="")
                messagebox.showerror("Экспорт", str(e))

        Thread(target=do, daemon=True).start()

    ctk.CTkButton(sec, text="Экспортировать модель", width=180, command=start_export).grid(
        row=row, column=0, padx=12, pady=8, sticky="w"
    )
    return sec
