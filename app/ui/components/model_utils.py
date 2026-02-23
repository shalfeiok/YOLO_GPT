from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QCheckBox, QLineEdit, QMessageBox, QWidget

from app.config import PROJECT_ROOT


def find_latest_best_model(project_root: Path = PROJECT_ROOT) -> Path | None:
    """Return most recently modified runs/**/weights/best.pt path."""
    candidates = list(project_root.glob("runs/**/weights/best.pt"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def make_best_model_checkbox(parent: QWidget, line_edit: QLineEdit) -> QCheckBox:
    """Create checkbox that inserts latest best.pt path into a model path field."""
    checkbox = QCheckBox("Использовать лучшую последнюю обученную модель")

    def _on_toggled(checked: bool) -> None:
        if not checked:
            return
        best = find_latest_best_model()
        if best is None:
            checkbox.blockSignals(True)
            checkbox.setChecked(False)
            checkbox.blockSignals(False)
            QMessageBox.information(parent, "Модель не найдена", "best.pt в папке runs не найден.")
            return
        line_edit.setText(str(best.resolve()))

    checkbox.toggled.connect(_on_toggled)
    return checkbox

