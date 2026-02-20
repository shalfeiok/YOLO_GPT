"""
UI for Ultralytics Solutions: Distance, Heatmap, ObjectCounter, RegionCounter, SpeedEstimator, TrackZone.
"""

from __future__ import annotations

from threading import Thread
from tkinter import messagebox

import customtkinter as ctk

from app.features.ultralytics_solutions.domain import SOLUTION_TYPES, SolutionsConfig
from app.features.ultralytics_solutions.repository import load_solutions_config, save_solutions_config
from app.features.ultralytics_solutions.service import run_solution

DOC_URLS = {
    "DistanceCalculation": "https://docs.ultralytics.com/ru/guides/distance-calculation/",
    "Heatmap": "https://docs.ultralytics.com/ru/guides/heatmaps/",
    "ObjectCounter": "https://docs.ultralytics.com/ru/guides/object-counting/",
    "RegionCounter": "https://docs.ultralytics.com/ru/guides/region-counting/",
    "SpeedEstimator": "https://docs.ultralytics.com/ru/guides/speed-estimation/",
    "TrackZone": "https://docs.ultralytics.com/ru/guides/trackzone/",
}


def build_solutions_section(parent: ctk.CTkFrame) -> ctk.CTkFrame:
    sec = ctk.CTkFrame(parent, fg_color=("gray92", "gray24"), corner_radius=8, border_width=1)
    sec.grid_columnconfigure(1, weight=1)
    cfg = load_solutions_config()
    row = 0

    ctk.CTkLabel(sec, text="L. Ultralytics Solutions (видео)", font=ctk.CTkFont(weight="bold", size=14)).grid(
        row=row, column=0, columnspan=3, padx=12, pady=(12, 6), sticky="w"
    )
    row += 1
    ctk.CTkLabel(
        sec,
        text="Расчёт расстояния, тепловые карты, подсчёт объектов, подсчёт по регионам, оценка скорости, TrackZone. Запуск в отдельном окне (видео или камера).",
        wraplength=700,
        anchor="w",
        font=ctk.CTkFont(size=11),
    ).grid(row=row, column=0, columnspan=3, padx=12, pady=(0, 8), sticky="w")
    row += 1

    type_var = ctk.StringVar(value=cfg.solution_type if cfg.solution_type in SOLUTION_TYPES else "ObjectCounter")

    def open_doc() -> None:
        import webbrowser
        u = DOC_URLS.get(type_var.get(), DOC_URLS["ObjectCounter"])
        webbrowser.open(u)

    ctk.CTkButton(sec, text="ℹ️ Подробнее", width=120, fg_color=("gray75", "gray35"), command=open_doc).grid(
        row=row, column=0, padx=12, pady=(0, 8), sticky="w"
    )
    row += 1

    ctk.CTkLabel(sec, text="Решение:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    ctk.CTkOptionMenu(sec, variable=type_var, values=SOLUTION_TYPES, width=200).grid(
        row=row, column=1, padx=8, pady=4, sticky="w"
    )
    row += 1

    ctk.CTkLabel(sec, text="Модель (.pt):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    model_e = ctk.CTkEntry(sec, width=380)
    model_e.insert(0, cfg.model_path)
    model_e.grid(row=row, column=1, padx=8, pady=4, sticky="ew")

    def browse_model() -> None:
        p = ctk.filedialog.askopenfilename(title="Модель", filetypes=[("PyTorch", "*.pt"), ("Все", "*.*")])
        if p:
            model_e.delete(0, "end")
            model_e.insert(0, p)
            c = load_solutions_config()
            c.model_path = p
            save_solutions_config(c)

    ctk.CTkButton(sec, text="Обзор…", width=80, command=browse_model).grid(row=row, column=2, padx=4, pady=4)
    row += 1

    ctk.CTkLabel(sec, text="Видео (путь или 0 = камера):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    source_e = ctk.CTkEntry(sec, width=380, placeholder_text="0 или path/to/video.mp4")
    source_e.insert(0, cfg.source)
    source_e.grid(row=row, column=1, padx=8, pady=4, sticky="ew")

    def browse_video() -> None:
        p = ctk.filedialog.askopenfilename(
            title="Видео",
            filetypes=[("Видео", "*.mp4 *.avi *.mkv"), ("Все", "*.*")],
        )
        if p:
            source_e.delete(0, "end")
            source_e.insert(0, p)
            c = load_solutions_config()
            c.source = p
            save_solutions_config(c)

    ctk.CTkButton(sec, text="Обзор…", width=80, command=browse_video).grid(row=row, column=2, padx=4, pady=4)
    row += 1

    ctk.CTkLabel(sec, text="Сохранить видео (пусто = не сохранять):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    out_e = ctk.CTkEntry(sec, width=380)
    out_e.insert(0, cfg.output_path)
    out_e.grid(row=row, column=1, padx=8, pady=4, sticky="ew")
    row += 1

    ctk.CTkLabel(sec, text="region (линия/полигон):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    region_e = ctk.CTkEntry(sec, width=380, placeholder_text="[(20,400), (1260,400)]")
    region_e.insert(0, cfg.region_points)
    region_e.grid(row=row, column=1, padx=8, pady=4, sticky="ew")
    row += 1

    ctk.CTkLabel(sec, text="FPS (для SpeedEstimator):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    fps_e = ctk.CTkEntry(sec, width=80)
    fps_e.insert(0, str(cfg.fps))
    fps_e.grid(row=row, column=1, padx=8, pady=4, sticky="w")
    row += 1

    prog_l = ctk.CTkLabel(sec, text="", font=ctk.CTkFont(size=10), text_color=("gray40", "gray55"))
    prog_l.grid(row=row, column=0, columnspan=3, padx=12, pady=4, sticky="w")
    row += 1

    def save_ui() -> None:
        c = load_solutions_config()
        c.solution_type = type_var.get()
        c.model_path = model_e.get().strip()
        c.source = source_e.get().strip()
        c.output_path = out_e.get().strip()
        c.region_points = region_e.get().strip() or "[(20, 400), (1260, 400)]"
        try:
            c.fps = float(fps_e.get())
        except ValueError:
            c.fps = 30.0
        save_solutions_config(c)

    def run() -> None:
        save_ui()
        cfg2 = load_solutions_config()
        if not cfg2.model_path:
            messagebox.showwarning("Solutions", "Укажите модель (.pt).")
            return

        def do() -> None:
            try:
                def prog(msg: str) -> None:
                    prog_l.configure(text=msg)
                    sec.update_idletasks()

                run_solution(cfg2, on_progress=prog)
                prog_l.configure(text="Готово.")
                messagebox.showinfo("Solutions", "Решение завершено. Окно отображения закрыто.")
            except Exception as e:
                prog_l.configure(text="")
                messagebox.showerror("Solutions", str(e))

        Thread(target=do, daemon=True).start()

    ctk.CTkButton(sec, text="Запустить решение", width=180, command=run).grid(row=row, column=0, padx=12, pady=8, sticky="w")
    return sec
