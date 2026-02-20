"""
UI section for SAHI tiled inference.

Ref: https://docs.ultralytics.com/ru/guides/sahi-tiled-inference/
"""

from __future__ import annotations

from pathlib import Path
from threading import Thread
from tkinter import messagebox

import customtkinter as ctk

from app.features.sahi_integration.domain import SahiConfig
from app.features.sahi_integration.repository import load_sahi_config, save_sahi_config
from app.features.sahi_integration.service import run_sahi_predict

DOC_URL = "https://docs.ultralytics.com/ru/guides/sahi-tiled-inference/"


def build_sahi_section(parent: ctk.CTkFrame) -> ctk.CTkFrame:
    sec = ctk.CTkFrame(parent, fg_color=("gray92", "gray24"), corner_radius=8, border_width=1)
    sec.grid_columnconfigure(1, weight=1)

    cfg = load_sahi_config()
    row = 0

    ctk.CTkLabel(
        sec,
        text="I. SAHI — инференс по срезам (большие изображения)",
        font=ctk.CTkFont(weight="bold", size=14),
    ).grid(row=row, column=0, columnspan=3, padx=12, pady=(12, 6), sticky="w")
    row += 1
    ctk.CTkLabel(
        sec,
        text="Разбиение больших изображений на срезы, детекция на каждом и объединение результатов. Требуется: pip install sahi",
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

    ctk.CTkLabel(sec, text="Модель (.pt):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    model_entry = ctk.CTkEntry(sec, width=400)
    model_entry.insert(0, cfg.model_path)
    model_entry.grid(row=row, column=1, padx=8, pady=4, sticky="ew")

    def browse_model() -> None:
        p = ctk.filedialog.askopenfilename(title="Модель YOLO", filetypes=[("PyTorch", "*.pt"), ("Все", "*.*")])
        if p:
            model_entry.delete(0, "end")
            model_entry.insert(0, p)
            c = load_sahi_config()
            c.model_path = p
            save_sahi_config(c)

    ctk.CTkButton(sec, text="Обзор…", width=80, command=browse_model).grid(row=row, column=2, padx=4, pady=4)
    row += 1

    ctk.CTkLabel(sec, text="Папка с изображениями:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    source_entry = ctk.CTkEntry(sec, width=400)
    source_entry.insert(0, cfg.source_dir)
    source_entry.grid(row=row, column=1, padx=8, pady=4, sticky="ew")

    def browse_source() -> None:
        p = ctk.filedialog.askdirectory(title="Папка с изображениями")
        if p:
            source_entry.delete(0, "end")
            source_entry.insert(0, p)
            c = load_sahi_config()
            c.source_dir = p
            save_sahi_config(c)

    ctk.CTkButton(sec, text="Обзор…", width=80, command=browse_source).grid(row=row, column=2, padx=4, pady=4)
    row += 1

    ctk.CTkLabel(sec, text="Размер среза (высота x ширина):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    sh_var = ctk.IntVar(value=cfg.slice_height)
    sw_var = ctk.IntVar(value=cfg.slice_width)
    ctk.CTkEntry(sec, width=70, textvariable=sh_var).grid(row=row, column=1, padx=8, pady=4, sticky="w")
    ctk.CTkLabel(sec, text="×").grid(row=row, column=1, padx=(85, 4), pady=4, sticky="w")
    ctk.CTkEntry(sec, width=70, textvariable=sw_var).grid(row=row, column=1, padx=(100, 0), pady=4, sticky="w")
    row += 1

    ctk.CTkLabel(sec, text="Перекрытие (height, width ratio):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    oh_var = ctk.DoubleVar(value=cfg.overlap_height_ratio)
    ow_var = ctk.DoubleVar(value=cfg.overlap_width_ratio)
    ctk.CTkEntry(sec, width=70, textvariable=oh_var).grid(row=row, column=1, padx=8, pady=4, sticky="w")
    ctk.CTkEntry(sec, width=70, textvariable=ow_var).grid(row=row, column=1, padx=(90, 0), pady=4, sticky="w")
    row += 1

    progress_label = ctk.CTkLabel(sec, text="", font=ctk.CTkFont(size=10), text_color=("gray40", "gray55"))
    progress_label.grid(row=row, column=0, columnspan=3, padx=12, pady=4, sticky="w")
    row += 1

    def save_ui() -> None:
        c = load_sahi_config()
        c.model_path = model_entry.get().strip()
        c.source_dir = source_entry.get().strip()
        c.slice_height = max(64, sh_var.get())
        c.slice_width = max(64, sw_var.get())
        c.overlap_height_ratio = max(0.0, min(1.0, oh_var.get()))
        c.overlap_width_ratio = max(0.0, min(1.0, ow_var.get()))
        save_sahi_config(c)

    def start_sahi() -> None:
        save_ui()
        cfg2 = load_sahi_config()
        if not cfg2.model_path:
            messagebox.showwarning("SAHI", "Укажите путь к модели (.pt).")
            return
        if not cfg2.source_dir or not Path(cfg2.source_dir).exists():
            messagebox.showwarning("SAHI", "Укажите существующую папку с изображениями.")
            return

        def do() -> None:
            try:
                def prog(msg: str) -> None:
                    progress_label.configure(text=msg)
                    sec.update_idletasks()

                run_sahi_predict(cfg2, on_progress=prog)
                progress_label.configure(text="Готово.")
                messagebox.showinfo("SAHI", "Инференс завершён. Результаты в папке с изображениями.")
            except ImportError as e:
                progress_label.configure(text="")
                messagebox.showerror("SAHI", "Установите SAHI: pip install sahi")
            except Exception as e:
                progress_label.configure(text="")
                messagebox.showerror("SAHI", str(e))

        Thread(target=do, daemon=True).start()

    ctk.CTkButton(sec, text="Запустить SAHI инференс", width=200, command=start_sahi).grid(
        row=row, column=0, padx=12, pady=8, sticky="w"
    )
    return sec
