"""
UI for isolating segmentation objects (mask → save crops).

Ref: https://docs.ultralytics.com/ru/guides/isolating-segmentation-objects/
"""

from __future__ import annotations

from pathlib import Path
from threading import Thread
from tkinter import messagebox

import customtkinter as ctk

from app.features.segmentation_isolation.domain import SegIsolationConfig
from app.features.segmentation_isolation.repository import load_seg_isolation_config, save_seg_isolation_config
from app.features.segmentation_isolation.service import run_seg_isolation

DOC_URL = "https://docs.ultralytics.com/ru/guides/isolating-segmentation-objects/"


def build_seg_isolation_section(parent: ctk.CTkFrame) -> ctk.CTkFrame:
    sec = ctk.CTkFrame(parent, fg_color=("gray92", "gray24"), corner_radius=8, border_width=1)
    sec.grid_columnconfigure(1, weight=1)
    cfg = load_seg_isolation_config()
    row = 0

    ctk.CTkLabel(sec, text="J. Изоляция объектов сегментации", font=ctk.CTkFont(weight="bold", size=14)).grid(
        row=row, column=0, columnspan=3, padx=12, pady=(12, 6), sticky="w"
    )
    row += 1
    ctk.CTkLabel(
        sec,
        text="Модель сегментации (seg): предсказание → маска по контуру → изолированный объект (чёрный или прозрачный фон), сохранение в PNG.",
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

    ctk.CTkLabel(sec, text="Модель (seg .pt):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    model_e = ctk.CTkEntry(sec, width=380)
    model_e.insert(0, cfg.model_path)
    model_e.grid(row=row, column=1, padx=8, pady=4, sticky="ew")

    def browse_model() -> None:
        p = ctk.filedialog.askopenfilename(title="Модель сегментации", filetypes=[("PyTorch", "*.pt"), ("Все", "*.*")])
        if p:
            model_e.delete(0, "end")
            model_e.insert(0, p)
            c = load_seg_isolation_config()
            c.model_path = p
            save_seg_isolation_config(c)

    ctk.CTkButton(sec, text="Обзор…", width=80, command=browse_model).grid(row=row, column=2, padx=4, pady=4)
    row += 1

    ctk.CTkLabel(sec, text="Изображение или папка:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    source_e = ctk.CTkEntry(sec, width=380)
    source_e.insert(0, cfg.source_path)
    source_e.grid(row=row, column=1, padx=8, pady=4, sticky="ew")

    def browse_source() -> None:
        p = ctk.filedialog.askopenfilename(
            title="Изображение",
            filetypes=[("Изображения", "*.jpg *.jpeg *.png *.bmp"), ("Все", "*.*")],
        )
        if not p:
            p = ctk.filedialog.askdirectory(title="Папка с изображениями")
        if p:
            source_e.delete(0, "end")
            source_e.insert(0, p)
            c = load_seg_isolation_config()
            c.source_path = p
            save_seg_isolation_config(c)

    ctk.CTkButton(sec, text="Обзор…", width=80, command=browse_source).grid(row=row, column=2, padx=4, pady=4)
    row += 1

    ctk.CTkLabel(sec, text="Папка сохранения:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    out_e = ctk.CTkEntry(sec, width=380, placeholder_text="runs/seg_isolation")
    out_e.insert(0, cfg.output_dir)
    out_e.grid(row=row, column=1, padx=8, pady=4, sticky="ew")
    row += 1

    ctk.CTkLabel(sec, text="Фон:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    bg_var = ctk.StringVar(value=cfg.background)
    ctk.CTkOptionMenu(sec, variable=bg_var, values=["black", "transparent"], width=140).grid(
        row=row, column=1, padx=8, pady=4, sticky="w"
    )
    row += 1

    crop_var = ctk.BooleanVar(value=cfg.crop)
    ctk.CTkCheckBox(sec, text="Обрезать по bbox", variable=crop_var).grid(row=row, column=0, columnspan=2, padx=12, pady=4, sticky="w")
    row += 1

    prog_l = ctk.CTkLabel(sec, text="", font=ctk.CTkFont(size=10), text_color=("gray40", "gray55"))
    prog_l.grid(row=row, column=0, columnspan=3, padx=12, pady=4, sticky="w")
    row += 1

    def save_ui() -> None:
        c = load_seg_isolation_config()
        c.model_path = model_e.get().strip()
        c.source_path = source_e.get().strip()
        c.output_dir = out_e.get().strip()
        c.background = bg_var.get()
        c.crop = crop_var.get()
        save_seg_isolation_config(c)

    def run() -> None:
        save_ui()
        cfg2 = load_seg_isolation_config()
        if not cfg2.model_path or not cfg2.source_path:
            messagebox.showwarning("Сегментация", "Укажите модель и источник.")
            return

        def do() -> None:
            try:
                def prog(msg: str) -> None:
                    prog_l.configure(text=msg)
                    sec.update_idletasks()

                n = run_seg_isolation(cfg2, on_progress=prog)
                prog_l.configure(text=f"Сохранено изображений: {n}")
                messagebox.showinfo("Сегментация", f"Сохранено изображений: {n}")
            except Exception as e:
                prog_l.configure(text="")
                messagebox.showerror("Сегментация", str(e))

        Thread(target=do, daemon=True).start()

    ctk.CTkButton(sec, text="Запустить изоляцию", width=180, command=run).grid(row=row, column=0, padx=12, pady=8, sticky="w")
    return sec
