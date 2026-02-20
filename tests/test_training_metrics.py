"""Тесты разбора строк лога обучения (training_metrics)."""
import pytest

from app.training_metrics import parse_metrics_line, parse_progress_line


class TestParseMetricsLine:
    """Парсинг строки метрик (all  gpu_mem  instances  box  cls  dfl  size)."""

    def test_returns_none_for_empty(self) -> None:
        assert parse_metrics_line("") is None
        assert parse_metrics_line("  \n  ") is None

    def test_returns_none_for_plain_text(self) -> None:
        assert parse_metrics_line("hello") is None
        assert parse_metrics_line("Epoch 1/50") is None

    def test_parses_metrics_line(self) -> None:
        line = "      all        944      40071       0.27       0.19      0.118     0.0599"
        out = parse_metrics_line(line)
        assert out is not None
        assert out["gpu_mem"] == 944
        assert out["instances"] == 40071
        assert out["box_loss"] == 0.27
        assert out["cls_loss"] == 0.19
        assert out["dfl_loss"] == 0.118
        assert out["size"] == 0.0599

    def test_parses_with_leading_spaces(self) -> None:
        line = " all 1 2 0.1 0.2 0.3 0.4"
        out = parse_metrics_line(line)
        assert out is not None
        assert out["gpu_mem"] == 1
        assert out["box_loss"] == 0.1


class TestParseProgressLine:
    """Парсинг строки прогресса батча (epoch, gpu, losses, batch_pct)."""

    def test_returns_none_for_empty(self) -> None:
        assert parse_progress_line("") is None

    def test_returns_none_for_metrics_line(self) -> None:
        assert parse_progress_line("      all        944      40071       0.27") is None

    def test_parses_progress_line(self) -> None:
        line = "       1/50      9.15G      2.831       2.03   0.002754        423        640: 80%"
        out = parse_progress_line(line)
        assert out is not None
        assert out["epoch"] == 1
        assert out["epoch_total"] == 50
        assert out["gpu_mem"] == 9.15
        assert out["box_loss"] == 2.831
        assert out["batch_pct"] == 80

    def test_parses_without_G_suffix(self) -> None:
        line = " 1/10 5.0 1.0 1.0 1.0 100 640: 50%"
        out = parse_progress_line(line)
        assert out is not None
        assert out["epoch"] == 1
        assert out["epoch_total"] == 10
        assert out["gpu_mem"] == 5.0
        assert out["batch_pct"] == 50
