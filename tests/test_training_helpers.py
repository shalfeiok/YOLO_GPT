"""Тесты вспомогательных функций вкладки «Обучение» (scan_trained_weights)."""
from pathlib import Path

import pytest

from app.ui.training.helpers import scan_trained_weights


class TestScanTrainedWeights:
    """Поиск runs/train/*/weights/best.pt."""

    def test_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        result = scan_trained_weights(tmp_path)
        assert result == []

    def test_no_runs_dir_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "other").mkdir()
        result = scan_trained_weights(tmp_path)
        assert result == []

    def test_finds_best_pt(self, tmp_path: Path) -> None:
        (tmp_path / "runs" / "train" / "exp1" / "weights").mkdir(parents=True)
        (tmp_path / "runs" / "train" / "exp1" / "weights" / "best.pt").write_bytes(b"x")
        result = scan_trained_weights(tmp_path)
        assert len(result) == 1
        label, path = result[0]
        assert "Наша:" in label
        assert path.name == "best.pt"
        assert path.exists()

    def test_multiple_runs(self, tmp_path: Path) -> None:
        for name in ("exp1", "exp2"):
            (tmp_path / "runs" / "train" / name / "weights").mkdir(parents=True)
            (tmp_path / "runs" / "train" / name / "weights" / "best.pt").write_bytes(b"x")
        result = scan_trained_weights(tmp_path)
        assert len(result) == 2
        labels = [r[0] for r in result]
        assert any("exp1" in l for l in labels)
        assert any("exp2" in l for l in labels)

    def test_ignores_dir_without_best_pt(self, tmp_path: Path) -> None:
        (tmp_path / "runs" / "train" / "no_weights").mkdir(parents=True)
        result = scan_trained_weights(tmp_path)
        assert result == []
