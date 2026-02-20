"""
Launchers for Streamlit live inference and Custom trainer template.

Refs: streamlit-live-inference, custom-trainer
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

STREAMLIT_DOC = "https://docs.ultralytics.com/ru/guides/streamlit-live-inference/"
CUSTOM_TRAINER_DOC = "https://docs.ultralytics.com/ru/guides/custom-trainer/"

STREAMLIT_SCRIPT = '''"""Streamlit Live Inference - Ultralytics YOLO. Run: streamlit run this_file.py"""
from ultralytics import solutions
MODEL_PATH = "yolo11n.pt"  # replaced by launcher
inf = solutions.Inference(model=MODEL_PATH)
inf.inference()
'''

CUSTOM_TRAINER_TEMPLATE = '''"""Custom Trainer template - Ultralytics. Ref: https://docs.ultralytics.com/ru/guides/custom-trainer/"""
from ultralytics import YOLO
from ultralytics.models.yolo.detect import DetectionTrainer

class CustomTrainer(DetectionTrainer):
    """Override validate(), save_model(), get_model(), etc."""
    def validate(self):
        metrics, fitness = super().validate()
        # Add custom metrics (e.g. F1 per class)
        return metrics, fitness

if __name__ == "__main__":
    model = YOLO("yolo11n.pt")
    model.train(data="coco8.yaml", epochs=10, trainer=CustomTrainer)
'''


def build_guides_launchers_section(parent: ctk.CTkFrame) -> ctk.CTkFrame:
    sec = ctk.CTkFrame(parent, fg_color=("gray92", "gray24"), corner_radius=8, border_width=1)
    sec.grid_columnconfigure(1, weight=1)
    row = 0

    ctk.CTkLabel(sec, text="M. Гайды: Streamlit, Custom Trainer", font=ctk.CTkFont(weight="bold", size=14)).grid(
        row=row, column=0, columnspan=3, padx=12, pady=(12, 6), sticky="w"
    )
    row += 1
    ctk.CTkLabel(
        sec,
        text="Запуск Streamlit live inference или сохранение шаблона Custom Trainer для доработки под ваши задачи.",
        wraplength=700,
        anchor="w",
        font=ctk.CTkFont(size=11),
    ).grid(row=row, column=0, columnspan=3, padx=12, pady=(0, 8), sticky="w")
    row += 1

    # Streamlit
    ctk.CTkLabel(sec, text="Модель для Streamlit:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    streamlit_model_e = ctk.CTkEntry(sec, width=380, placeholder_text="yolo11n.pt")
    streamlit_model_e.grid(row=row, column=1, padx=8, pady=4, sticky="ew")

    def browse_streamlit_model() -> None:
        p = ctk.filedialog.askopenfilename(title="Модель", filetypes=[("PyTorch", "*.pt"), ("Все", "*.*")])
        if p:
            streamlit_model_e.delete(0, "end")
            streamlit_model_e.insert(0, p)

    ctk.CTkButton(sec, text="Обзор…", width=80, command=browse_streamlit_model).grid(row=row, column=2, padx=4, pady=4)
    row += 1

    def launch_streamlit() -> None:
        model = streamlit_model_e.get().strip() or "yolo11n.pt"
        try:
            import streamlit
        except ImportError:
            messagebox.showerror("Streamlit", "Установите: pip install streamlit")
            return
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(STREAMLIT_SCRIPT.replace('MODEL_PATH = "yolo11n.pt"', f"MODEL_PATH = {repr(model)}"))
            path = f.name
        try:
            subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", path, "--server.headless", "true"],
                creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0,
            )
            messagebox.showinfo("Streamlit", "Streamlit запущен в браузере. Закройте консоль при необходимости.")
        except Exception as e:
            messagebox.showerror("Streamlit", str(e))

    ctk.CTkButton(sec, text="Запустить Streamlit inference", width=220, command=launch_streamlit).grid(
        row=row, column=0, columnspan=2, padx=12, pady=4, sticky="w"
    )

    def open_streamlit_doc() -> None:
        import webbrowser
        webbrowser.open(STREAMLIT_DOC)

    ctk.CTkButton(sec, text="Документация", width=100, fg_color=("gray70", "gray30"), command=open_streamlit_doc).grid(
        row=row, column=2, padx=4, pady=4
    )
    row += 1

    # Custom Trainer template
    ctk.CTkLabel(sec, text="Путь для шаблона Custom Trainer:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    template_path_e = ctk.CTkEntry(sec, width=380, placeholder_text="custom_trainer_example.py")
    template_path_e.grid(row=row, column=1, padx=8, pady=4, sticky="ew")

    def save_custom_trainer_template() -> None:
        p = template_path_e.get().strip() or "custom_trainer_example.py"
        if not p.endswith(".py"):
            p += ".py"
        path = Path(p)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(CUSTOM_TRAINER_TEMPLATE, encoding="utf-8")
        messagebox.showinfo("Custom Trainer", f"Шаблон сохранён: {path}")

    ctk.CTkButton(sec, text="Сохранить шаблон", width=140, command=save_custom_trainer_template).grid(
        row=row, column=2, padx=4, pady=4
    )
    row += 1

    def open_custom_doc() -> None:
        import webbrowser
        webbrowser.open(CUSTOM_TRAINER_DOC)

    ctk.CTkButton(sec, text="Документация Custom Trainer", width=200, fg_color=("gray70", "gray30"), command=open_custom_doc).grid(
        row=row, column=0, columnspan=2, padx=12, pady=8, sticky="w"
    )
    return sec
