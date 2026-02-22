from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_worker_module():
    mod_path = Path("app/ui/views/datasets/worker.py")
    spec = importlib.util.spec_from_file_location("dataset_worker_module", mod_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_prepare_yolo_rejects_empty_output_for_non_voc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_worker_module()
    DatasetWorker = mod.DatasetWorker

    src = tmp_path / "src"
    src.mkdir()

    monkeypatch.setattr(mod, "is_voc_dataset", lambda _p: False)
    monkeypatch.setattr(mod, "prepare_for_yolo", lambda *_args, **_kwargs: None)

    worker = DatasetWorker()
    worker.set_task("prepare_yolo", {"src": str(src), "out": "   "})

    with pytest.raises(ValueError, match="Укажите папку, куда сохранить YOLO-датасет"):
        worker._run_prepare_yolo()


def test_augment_rejects_empty_output_path(tmp_path: Path) -> None:
    mod = _load_worker_module()
    DatasetWorker = mod.DatasetWorker

    src = tmp_path / "src"
    src.mkdir()

    worker = DatasetWorker()
    worker.set_task("augment", {"src": str(src), "out": "", "opts": {"flip": True}})

    with pytest.raises(ValueError, match="Укажите папку для нового датасета"):
        worker._run_augment()
