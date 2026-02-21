"""Thin UI adapters for common file dialogs.

Keeping QFileDialog usage in one place makes the rest of the UI easier to test and keeps
view code focused on composition and binding.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

try:
    _qt_widgets = import_module("PySide6.QtWidgets")
    QFileDialog = getattr(_qt_widgets, "QFileDialog", None)
except Exception:  # pragma: no cover
    QFileDialog = None


def get_open_json_path(parent: QWidget | None = None, *, title: str = "Open", start_dir: Path | None = None) -> Path | None:
    if QFileDialog is None:
        return None
    start = str(start_dir or Path.home())
    path, _ = cast(Any, QFileDialog).getOpenFileName(parent, title, start, "JSON (*.json);;All files (*.*)")
    return Path(path) if path else None


def get_save_json_path(parent: QWidget | None = None, *, title: str = "Save", start_dir: Path | None = None) -> Path | None:
    if QFileDialog is None:
        return None
    start = str(start_dir or Path.home())
    path, _ = cast(Any, QFileDialog).getSaveFileName(parent, title, start, "JSON (*.json);;All files (*.*)")
    return Path(path) if path else None


def get_open_yaml_path(parent: QWidget | None = None, *, title: str = "Open", start_dir: Path | None = None) -> Path | None:
    """Open a YAML file."""
    if QFileDialog is None:
        return None
    start = str(start_dir or Path.home())
    path, _ = cast(Any, QFileDialog).getOpenFileName(parent, title, start, "YAML (*.yaml *.yml);;All files (*.*)")
    return Path(path) if path else None


def get_open_pt_path(parent: QWidget | None = None, *, title: str = "Open", start_dir: Path | None = None) -> Path | None:
    """Open a PyTorch weights file (.pt)."""
    if QFileDialog is None:
        return None
    start = str(start_dir or Path.home())
    path, _ = cast(Any, QFileDialog).getOpenFileName(parent, title, start, "PyTorch (*.pt);;All files (*.*)")
    return Path(path) if path else None


def get_open_model_or_yaml_path(parent: QWidget | None = None, *, title: str = "Open", start_dir: Path | None = None) -> Path | None:
    """Open a model config/weights file (pt or yaml)."""
    if QFileDialog is None:
        return None
    start = str(start_dir or Path.home())
    path, _ = cast(Any, QFileDialog).getOpenFileName(parent, title, start, "PyTorch (*.pt);;YAML (*.yaml *.yml);;All files (*.*)")
    return Path(path) if path else None


def get_existing_dir(parent: QWidget | None = None, *, title: str = "Select folder", start_dir: Path | None = None) -> Path | None:
    """Select an existing directory."""
    if QFileDialog is None:
        return None
    start = str(start_dir or Path.home())
    path = cast(Any, QFileDialog).getExistingDirectory(parent, title, start)
    return Path(path) if path else None


def get_save_zip_path(parent: QWidget | None = None, *, title: str = "Save", start_dir: Path | None = None) -> Path | None:
    if QFileDialog is None:
        return None
    start = str(start_dir or Path.home())
    path, _ = cast(Any, QFileDialog).getSaveFileName(parent, title, start, "ZIP (*.zip);;All files (*.*)")
    return Path(path) if path else None
