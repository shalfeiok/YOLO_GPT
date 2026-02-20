"""Thin UI adapters for common file dialogs.

Keeping QFileDialog usage in one place makes the rest of the UI easier to test and keeps
view code focused on composition and binding.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

try:
    from PySide6.QtWidgets import QFileDialog, QWidget
except Exception:  # pragma: no cover
    QFileDialog = None  # type: ignore[assignment]
    QWidget = object  # type: ignore[assignment]

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget as _QWidget


def get_open_json_path(parent: "_QWidget | None" = None, *, title: str = "Open", start_dir: Path | None = None) -> Path | None:
    if QFileDialog is None:
        return None
    start = str(start_dir or Path.home())
    path, _ = QFileDialog.getOpenFileName(parent, title, start, "JSON (*.json);;All files (*.*)")
    return Path(path) if path else None


def get_save_json_path(parent: "_QWidget | None" = None, *, title: str = "Save", start_dir: Path | None = None) -> Path | None:
    if QFileDialog is None:
        return None
    start = str(start_dir or Path.home())
    path, _ = QFileDialog.getSaveFileName(parent, title, start, "JSON (*.json);;All files (*.*)")
    return Path(path) if path else None


def get_open_yaml_path(parent: "_QWidget | None" = None, *, title: str = "Open", start_dir: Path | None = None) -> Path | None:
    """Open a YAML file."""
    if QFileDialog is None:
        return None
    start = str(start_dir or Path.home())
    path, _ = QFileDialog.getOpenFileName(parent, title, start, "YAML (*.yaml *.yml);;All files (*.*)")
    return Path(path) if path else None


def get_open_pt_path(parent: "_QWidget | None" = None, *, title: str = "Open", start_dir: Path | None = None) -> Path | None:
    """Open a PyTorch weights file (.pt)."""
    if QFileDialog is None:
        return None
    start = str(start_dir or Path.home())
    path, _ = QFileDialog.getOpenFileName(parent, title, start, "PyTorch (*.pt);;All files (*.*)")
    return Path(path) if path else None


def get_open_model_or_yaml_path(parent: "_QWidget | None" = None, *, title: str = "Open", start_dir: Path | None = None) -> Path | None:
    """Open a model config/weights file (pt or yaml)."""
    if QFileDialog is None:
        return None
    start = str(start_dir or Path.home())
    path, _ = QFileDialog.getOpenFileName(parent, title, start, "PyTorch (*.pt);;YAML (*.yaml *.yml);;All files (*.*)")
    return Path(path) if path else None


def get_existing_dir(parent: "_QWidget | None" = None, *, title: str = "Select folder", start_dir: Path | None = None) -> Path | None:
    """Select an existing directory."""
    if QFileDialog is None:
        return None
    start = str(start_dir or Path.home())
    path = QFileDialog.getExistingDirectory(parent, title, start)
    return Path(path) if path else None


def get_save_zip_path(parent: "_QWidget | None" = None, *, title: str = "Save", start_dir: Path | None = None) -> Path | None:
    if QFileDialog is None:
        return None
    start = str(start_dir or Path.home())
    path, _ = QFileDialog.getSaveFileName(parent, title, start, "ZIP (*.zip);;All files (*.*)")
    return Path(path) if path else None
