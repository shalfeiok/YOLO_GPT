"""Parse Ultralytics training log lines for live metrics UI."""

import re

# Ultralytics validation line like:
# "all 944 40071 0.27 0.19 0.118 0.0599"
_METRICS_RE = re.compile(
    r"\ball\s+(\d+)\s+(\d+)\s+([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
    r"\s+([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
    r"\s+([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
    r"\s+([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*$"
)

# Строка прогресса эпохи: "       1/50      9.15G      2.831       2.03   0.002754        423        640: 80%"
_PROGRESS_RE = re.compile(
    r"(?P<epoch>\d+)\s*/\s*(?P<epoch_total>\d+)\s+"
    r"(?P<gpu_mem>[+-]?(?:\d+\.?\d*|\.\d+))\s*(?P<gpu_unit>[GM]?)\w*\s+"
    r"(?P<box_loss>[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s+"
    r"(?P<cls_loss>[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s+"
    r"(?P<dfl_loss>[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s+"
    r"(?P<instances>\d+)\s+"
    r"(?P<size>\d+)(?:\s*:\s*(?P<batch_pct>\d+)%?)?"
)


def parse_metrics_line(line: str) -> dict[str, float | int] | None:
    """If line is a validation metrics row (starts with 'all'), return dict; else None."""
    line = line.strip()
    m = _METRICS_RE.search(line)
    if not m:
        return None
    return {
        "images": int(m.group(1)),
        "instances": int(m.group(2)),
        "precision": float(m.group(3)),
        "recall": float(m.group(4)),
        "map50": float(m.group(5)),
        "map50_95": float(m.group(6)),
    }


def parse_progress_line(line: str) -> dict[str, float | int] | None:
    """Если строка — прогресс батча (1/50  9.15G  box  cls  dfl  instances  640: 80%), возвращает dict."""
    line = line.strip()
    m = _PROGRESS_RE.search(line)
    if not m:
        return None
    gpu_mem = float(m.group("gpu_mem"))
    gpu_unit = m.group("gpu_unit")
    if gpu_unit == "M":
        gpu_mem /= 1024.0

    batch_pct_raw = m.group("batch_pct")
    if batch_pct_raw is None:
        trailing_pct = re.search(r":\s*(\d+)%", line)
        batch_pct_raw = None if trailing_pct is None else trailing_pct.group(1)

    return {
        "epoch": int(m.group("epoch")),
        "epoch_total": int(m.group("epoch_total")),
        "gpu_mem": gpu_mem,
        "box_loss": float(m.group("box_loss")),
        "cls_loss": float(m.group("cls_loss")),
        "dfl_loss": float(m.group("dfl_loss")),
        "instances": int(m.group("instances")),
        "size": float(m.group("size")),
        "batch_pct": None if batch_pct_raw is None else int(batch_pct_raw),
    }
