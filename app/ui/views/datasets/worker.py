"""
Воркер для тяжёлых операций вкладки «Датасет». Выполняет задачи в отдельном потоке,
эмитит progress и finished, чтобы UI не зависал.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from app.application.facades.datasets import (
    convert_voc_to_yolo,
    create_augmented_dataset,
    export_dataset_filter_classes,
    is_voc_dataset,
    merge_classes_in_dataset,
    prepare_for_yolo,
    rename_class_in_dataset,
)


class DatasetWorker(QObject):
    """Выполняет одну задачу в потоке. Перед start задать task_id и params."""

    progress = Signal(float)  # 0..1
    finished = Signal(bool, str)  # success, message

    def __init__(self) -> None:
        super().__init__()
        self._task_id: str = ""
        self._params: dict[str, Any] = {}

    def set_task(self, task_id: str, params: dict[str, Any]) -> None:
        self._task_id = task_id
        self._params = params

    def run(self) -> None:
        self.progress.emit(0.0)
        try:
            if self._task_id == "prepare_yolo":
                self._run_prepare_yolo()
            elif self._task_id == "augment":
                self._run_augment()
            elif self._task_id == "export_classes":
                self._run_export_classes()
            elif self._task_id == "merge_classes":
                self._run_merge_classes()
            elif self._task_id == "rename_class":
                self._run_rename_class()
            else:
                self.finished.emit(False, f"Неизвестная задача: {self._task_id}")
                return
            self.progress.emit(1.0)
            self.finished.emit(True, self._params.get("result_message", "Готово."))
        except Exception as e:
            self.finished.emit(False, str(e))

    def _run_prepare_yolo(self) -> None:
        src = Path(self._params["src"])
        out = Path(self._params["out"])
        if not src.is_dir():
            raise FileNotFoundError("Укажите существующую исходную папку.")
        if is_voc_dataset(src):
            convert_voc_to_yolo(src)
            self._params["result_message"] = f"Pascal VOC конвертирован в YOLO.\nПуть: {src}"
        else:
            if not out:
                raise ValueError("Укажите папку, куда сохранить YOLO-датасет.")
            prepare_for_yolo(src, out)
            self._params["result_message"] = f"Датасет сохранён: {out}"

    def _run_augment(self) -> None:
        src = Path(self._params["src"])
        out = Path(self._params["out"])
        opts = self._params.get("opts", {})
        if not src.is_dir():
            raise FileNotFoundError("Укажите исходный датасет.")
        if not out:
            raise ValueError("Укажите папку для нового датасета.")
        if not any(opts.values()):
            raise ValueError("Отметьте хотя бы один вариант эффекта.")
        create_augmented_dataset(src, out, opts)
        self._params["result_message"] = f"Варианты созданы: {out}"

    def _run_export_classes(self) -> None:
        src = Path(self._params["src"])
        out = Path(self._params["out"])
        selected = self._params.get("selected", set())
        classes = self._params.get("classes", [])
        if not src.is_dir():
            raise FileNotFoundError("Укажите датасет.")
        if not out:
            raise ValueError("Укажите папку для экспорта.")
        if not selected:
            raise ValueError("Отметьте хотя бы один класс.")
        export_dataset_filter_classes(src, out, selected, classes)
        self._params["result_message"] = f"Экспорт: {out}"

    def _run_merge_classes(self) -> None:
        src = Path(self._params["src"])
        out = Path(self._params["out"])
        to_merge = self._params.get("to_merge", set())
        new_name = self._params.get("new_name", "merged")
        class_names = self._params.get("class_names", [])
        if not src.is_dir():
            raise FileNotFoundError("Укажите датасет.")
        if not out:
            raise ValueError("Укажите папку для нового датасета.")
        if len(to_merge) < 2:
            raise ValueError("Отметьте хотя бы два класса для объединения.")
        merge_classes_in_dataset(src, out, to_merge, new_name, class_names)
        self._params["result_message"] = f"Классы объединены. Новый датасет: {out}"

    def _run_rename_class(self) -> None:
        src = Path(self._params["src"])
        old_name = self._params.get("old_name", "")
        new_name = self._params.get("new_name", "")
        if not src.is_dir():
            raise FileNotFoundError("Укажите датасет.")
        if not old_name or not new_name:
            raise ValueError("Выберите класс и введите новое имя.")
        rename_class_in_dataset(src, new_name=new_name, old_name=old_name)
        self._params["result_message"] = f"Класс «{old_name}» переименован в «{new_name}»."
