from __future__ import annotations

from app.application.use_cases.train_model import normalize_training_device


def test_normalize_cuda_style() -> None:
    assert normalize_training_device("cuda:0") == "0"
    assert normalize_training_device("cuda:1") == "1"


def test_normalize_cpu_and_index_list() -> None:
    assert normalize_training_device("cpu") == "cpu"
    assert normalize_training_device("0,1") == "0,1"


def test_normalize_auto(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.application.use_cases.train_model._cuda_available",
        lambda: False,
    )
    assert normalize_training_device("auto") == "cpu"
