"""
UI section for Albumentations: checkbox, standard/custom, edit transforms, p slider, description.

Ref: https://docs.ultralytics.com/ru/integrations/albumentations/
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.features.albumentations_integration.domain import AlbumentationsConfig, STANDARD_TRANSFORM_NAMES
from app.features.albumentations_integration.repository import load_albumentations_config, save_albumentations_config

DESCRIPTION = (
    "Albumentations — быстрая и гибкая библиотека аугментации изображений. "
    "Улучшает обобщающую способность модели за счёт 70+ преобразований. "
    "Интеграция с YOLO26 автоматически применяет трансформы при обучении."
)
DOC_URL = "https://docs.ultralytics.com/ru/integrations/albumentations/"


def build_albumentations_section(
    parent: ctk.CTkFrame,
    on_reset_defaults: Callable[[], None] | None = None,
) -> ctk.CTkFrame:
    """
    Build the Albumentations section frame. Call on_reset_defaults when user clicks reset.
    """
    sec = ctk.CTkFrame(parent, fg_color=("gray92", "gray24"), corner_radius=8, border_width=1)
    sec.grid_columnconfigure(1, weight=1)

    cfg = load_albumentations_config()
    row = 0

    # Title and description
    ctk.CTkLabel(
        sec,
        text="A. Аугментация данных (Albumentations)",
        font=ctk.CTkFont(weight="bold", size=14),
    ).grid(row=row, column=0, columnspan=3, padx=12, pady=(12, 6), sticky="w")
    row += 1
    desc = ctk.CTkLabel(sec, text=DESCRIPTION, wraplength=700, anchor="w", justify="left", font=ctk.CTkFont(size=11))
    desc.grid(row=row, column=0, columnspan=3, padx=12, pady=(0, 8), sticky="w")
    row += 1

    # Info link
    def open_doc() -> None:
        import webbrowser
        webbrowser.open(DOC_URL)

    ctk.CTkButton(sec, text="ℹ️ Подробнее", width=120, fg_color=("gray75", "gray35"), command=open_doc).grid(
        row=row, column=0, padx=12, pady=(0, 8), sticky="w"
    )
    row += 1

    # Enable checkbox
    enabled_var = ctk.BooleanVar(value=cfg.enabled)

    def save_enabled() -> None:
        c = load_albumentations_config()
        c.enabled = enabled_var.get()
        save_albumentations_config(c)

    ctk.CTkCheckBox(
        sec,
        text="Включить Albumentations во время обучения",
        variable=enabled_var,
        command=save_enabled,
    ).grid(row=row, column=0, columnspan=2, padx=12, pady=4, sticky="w")
    row += 1

    # Standard / Custom dropdown
    ctk.CTkLabel(sec, text="Режим:").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    mode_var = ctk.StringVar(value="Стандартные трансформы" if cfg.use_standard else "Кастомные трансформы")
    mode_menu = ctk.CTkOptionMenu(
        sec,
        variable=mode_var,
        values=["Стандартные трансформы", "Кастомные трансформы"],
        width=220,
        command=lambda _: _save_mode(),
    )

    def _save_mode() -> None:
        c = load_albumentations_config()
        c.use_standard = "Стандартные" in mode_var.get()
        save_albumentations_config(c)

    mode_menu.grid(row=row, column=1, padx=0, pady=4, sticky="w")
    row += 1

    # Edit custom transforms (opens simple list dialog)
    def edit_transforms() -> None:
        _open_transforms_editor(sec.winfo_toplevel(), sec)

    ctk.CTkButton(sec, text="Редактировать кастомные трансформы", width=260, command=edit_transforms).grid(
        row=row, column=0, columnspan=2, padx=12, pady=4, sticky="w"
    )
    row += 1

    # Probability p
    ctk.CTkLabel(sec, text="Вероятность (p):").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    p_var = ctk.DoubleVar(value=cfg.transform_p)
    p_slider = ctk.CTkSlider(sec, from_=0, to=1, variable=p_var, width=200, command=lambda v: _save_p(float(v)))
    p_slider.grid(row=row, column=1, padx=0, pady=4, sticky="w")
    p_label = ctk.CTkLabel(sec, text=f"{cfg.transform_p:.2f}")
    p_label.grid(row=row, column=2, padx=8, pady=4, sticky="w")

    def _save_p(v: float) -> None:
        p_label.configure(text=f"{v:.2f}")
        c = load_albumentations_config()
        c.transform_p = v
        save_albumentations_config(c)

    row += 1

    # Reset defaults
    if on_reset_defaults:

        def reset() -> None:
            default = AlbumentationsConfig(
                enabled=False,
                use_standard=True,
                custom_transforms=[],
                transform_p=0.5,
            )
            save_albumentations_config(default)
            enabled_var.set(default.enabled)
            mode_var.set("Стандартные трансформы" if default.use_standard else "Кастомные трансформы")
            p_var.set(default.transform_p)
            p_label.configure(text=f"{default.transform_p:.2f}")
            if on_reset_defaults:
                on_reset_defaults()

        ctk.CTkButton(sec, text="Сбросить настройки по умолчанию", width=220, fg_color=("gray70", "gray30"), command=reset).grid(
            row=row, column=0, columnspan=2, padx=12, pady=(8, 12), sticky="w"
        )

    return sec


def _open_transforms_editor(parent: ctk.CTkToplevel | ctk.CTk, section_frame: ctk.CTkFrame) -> None:
    """Open a simple window to add/remove custom transforms (name + p)."""
    cfg = load_albumentations_config()
    win = ctk.CTkToplevel(parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent)
    win.title("Кастомные трансформы Albumentations")
    win.geometry("480x400")
    win.grid_columnconfigure(0, weight=1)
    win.grid_rowconfigure(1, weight=1)

    list_frame = ctk.CTkScrollableFrame(win)
    list_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
    list_frame.grid_columnconfigure(0, weight=1)

    transforms: list[dict] = list(cfg.custom_transforms)

    def refresh_list() -> None:
        for w in list_frame.winfo_children():
            w.destroy()
        for i, t in enumerate(transforms):
            name = t.get("name", t.get("transform", "?"))
            p_val = t.get("p", 0.5)
            r = ctk.CTkFrame(list_frame, fg_color="transparent")
            r.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(r, text=name).grid(row=0, column=0, padx=4, pady=2, sticky="w")
            ctk.CTkLabel(r, text=f"p={p_val}").grid(row=0, column=1, padx=4, pady=2, sticky="w")

            def remove(idx: int) -> None:
                transforms.pop(idx)
                refresh_list()

            ctk.CTkButton(r, text="Удалить", width=70, command=lambda idx=i: remove(idx)).grid(row=0, column=2, padx=4, pady=2)
            r.grid(row=i, column=0, sticky="ew", pady=2)

    def add_transform() -> None:
        name_var = ctk.StringVar(value="Blur")
        add_win = ctk.CTkToplevel(win)
        add_win.title("Добавить трансформ")
        add_win.geometry("320x180")
        ctk.CTkLabel(add_win, text="Трансформ:").grid(row=0, column=0, padx=8, pady=8, sticky="w")
        ctk.CTkOptionMenu(add_win, variable=name_var, values=STANDARD_TRANSFORM_NAMES, width=200).grid(
            row=0, column=1, padx=8, pady=8, sticky="w"
        )
        ctk.CTkLabel(add_win, text="p (0-1):").grid(row=1, column=0, padx=8, pady=8, sticky="w")
        p_entry = ctk.CTkEntry(add_win, width=80)
        p_entry.insert(0, "0.5")
        p_entry.grid(row=1, column=1, padx=8, pady=8, sticky="w")

        def do_add() -> None:
            try:
                p = float(p_entry.get())
            except ValueError:
                p = 0.5
            transforms.append({"name": name_var.get(), "p": p})
            refresh_list()
            add_win.destroy()

        ctk.CTkButton(add_win, text="Добавить", command=do_add).grid(row=2, column=1, padx=8, pady=12, sticky="w")
        add_win.grab_set()

    refresh_list()

    ctk.CTkLabel(win, text="Кастомные трансформы (применяются при обучении):", font=ctk.CTkFont(weight="bold")).grid(
        row=0, column=0, padx=12, pady=(12, 4), sticky="w"
    )
    ctk.CTkButton(win, text="+ Добавить трансформ", command=add_transform).grid(row=2, column=0, padx=12, pady=8, sticky="w")

    def save_and_close() -> None:
        cfg.custom_transforms = transforms
        save_albumentations_config(cfg)
        win.destroy()

    ctk.CTkButton(win, text="Сохранить и закрыть", command=save_and_close).grid(row=3, column=0, padx=12, pady=(0, 12), sticky="w")
