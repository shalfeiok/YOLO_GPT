"""Parse training log lines for Epoch / GPU_mem / box_loss / cls_loss / dfl_loss / Instances / Size."""
import re
from typing import Optional

# Ultralytics line like: "      all        944      40071       0.27       0.19      0.118     0.0599"
_METRICS_RE = re.compile(
    r"\ball\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$"
)

# Строка прогресса эпохи: "       1/50      9.15G      2.831       2.03   0.002754        423        640: 80%"
_PROGRESS_RE = re.compile(
    r"(\d+)/(\d+)\s+([\d.]+)G?\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+\d+:\s*(\d+)%\s*"
)


def parse_metrics_line(line: str) -> Optional[dict[str, float]]:
    """If line is a metrics row (starts with 'all' and numbers), return dict; else None."""
    line = line.strip()
    m = _METRICS_RE.search(line)
    if not m:
        return None
    return {
        "gpu_mem": int(m.group(1)),
        "instances": int(m.group(2)),
        "box_loss": float(m.group(3)),
        "cls_loss": float(m.group(4)),
        "dfl_loss": float(m.group(5)),
        "size": float(m.group(6)),
    }


def parse_progress_line(line: str) -> Optional[dict[str, float | int]]:
    """Если строка — прогресс батча (1/50  9.15G  box  cls  dfl  instances  640: 80%), возвращает dict."""
    line = line.strip()
    m = _PROGRESS_RE.search(line)
    if not m:
        return None
    return {
        "epoch": int(m.group(1)),
        "epoch_total": int(m.group(2)),
        "gpu_mem": float(m.group(3)),
        "box_loss": float(m.group(4)),
        "cls_loss": float(m.group(5)),
        "dfl_loss": float(m.group(6)),
        "instances": int(m.group(7)),
        "batch_pct": int(m.group(8)),
    }
