"""
UI: диалог настроек выбранного бэкенда визуализации по схеме (get_settings_schema), сброс к стандарту.
"""
from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from app.features.detection_visualization.backends import get_backend
from app.features.detection_visualization.domain import (
    default_visualization_config,
    get_config_section,
)
from app.features.detection_visualization.repository import (
    load_visualization_config,
    save_visualization_config,
)


def open_visualization_settings_dialog(
    parent: ctk.CTk,
    backend_id: str,
    on_saved: None = None,
) -> None:
    """
    Открыть диалог настроек для бэкенда backend_id.
    Форма строится по backend.get_settings_schema().
    on_saved() вызывается после сохранения (можно обновить UI).
    """
    config = load_visualization_config()
    backend = get_backend(backend_id)
    section = get_config_section(backend_id)
    backend.apply_settings(config.get(section, {}))

    dialog = ctk.CTkToplevel(parent)
    dialog.title(f"Настройки: {backend.get_display_name()}")
    dialog.geometry("420x360")
    dialog.transient(parent)
    dialog.grab_set()

    main = ctk.CTkFrame(dialog, fg_color="transparent")
    main.pack(fill="both", expand=True, padx=16, pady=16)
    main.grid_columnconfigure(1, weight=1)

    row = 0
    entries: dict[str, ctk.CTkEntry] = {}
    check_vars: dict[str, ctk.BooleanVar] = {}
    combo_vars: dict[str, ctk.CTkComboBox] = {}
    defaults = backend.get_default_settings()
    settings = backend.get_settings()

    for field in backend.get_settings_schema():
        key = field.get("key")
        if not key:
            continue
        typ = field.get("type", "str")
        label_text = field.get("label", key)
        default = field.get("default", defaults.get(key))

        ctk.CTkLabel(main, text=label_text + ":").grid(row=row, column=0, padx=(0, 8), pady=4, sticky="w")
        row += 1

        if typ == "int":
            e = ctk.CTkEntry(main, width=100)
            e.insert(0, str(settings.get(key, default)))
            e.grid(row=row, column=1, padx=0, pady=4, sticky="w")
            entries[key] = e
        elif typ == "bool":
            v = ctk.BooleanVar(value=settings.get(key, default))
            check_vars[key] = v
            ctk.CTkCheckBox(main, text="", variable=v).grid(row=row, column=1, padx=0, pady=4, sticky="w")
        elif typ == "choice":
            choices = field.get("choices", [])
            current = str(settings.get(key, default))
            combo = ctk.CTkComboBox(main, values=choices, width=140)
            if current in choices:
                combo.set(current)
            elif choices:
                combo.set(choices[0])
            combo.grid(row=row, column=1, padx=0, pady=4, sticky="w")
            combo_vars[key] = combo
        else:
            e = ctk.CTkEntry(main, width=100)
            e.insert(0, str(settings.get(key, default)))
            e.grid(row=row, column=1, padx=0, pady=4, sticky="w")
            entries[key] = e
        row += 1

    def collect_settings() -> dict:
        out = {}
        for k, e in entries.items():
            try:
                out[k] = int(e.get().strip())
            except ValueError:
                out[k] = defaults.get(k, 0)
        for k, v in check_vars.items():
            out[k] = v.get()
        for k, c in combo_vars.items():
            out[k] = c.get()
        return out

    def save_and_close() -> None:
        new_settings = collect_settings()
        config[section] = new_settings
        save_visualization_config(config)
        backend.apply_settings(new_settings)
        if on_saved:
            on_saved()
        dialog.destroy()

    def reset_to_default() -> None:
        defs = backend.get_default_settings()
        for k, e in entries.items():
            e.delete(0, "end")
            e.insert(0, str(defs.get(k, "")))
        for k, v in check_vars.items():
            v.set(defs.get(k, False))
        for k, c in combo_vars.items():
            val = defs.get(k)
            if val is not None and hasattr(c, "set"):
                c.set(val)
        config[section] = dict(defs)
        save_visualization_config(config)
        messagebox.showinfo("Сброс", "Настройки сброшены к стандарту.", parent=dialog)

    btn_frame = ctk.CTkFrame(main, fg_color="transparent")
    btn_frame.grid(row=row, column=0, columnspan=2, pady=(16, 0), sticky="w")
    ctk.CTkButton(btn_frame, text="Сбросить к стандарту", width=160, command=reset_to_default).pack(side="left", padx=(0, 8))
    ctk.CTkButton(btn_frame, text="Сохранить", width=100, command=save_and_close).pack(side="left")


def reset_visualization_config_to_default() -> dict:
    """Сбросить конфиг визуализации к дефолту, сохранить и вернуть новый конфиг."""
    config = default_visualization_config()
    save_visualization_config(config)
    return config
