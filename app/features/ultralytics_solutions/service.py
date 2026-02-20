"""
Run Ultralytics Solutions (Distance, Heatmap, ObjectCounter, etc.) via generated script + subprocess.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

from app.features.ultralytics_solutions.domain import SolutionsConfig, SOLUTION_TYPES


def _script_content(cfg: SolutionsConfig) -> str:
    model = repr(cfg.model_path or "yolo11n.pt")
    source = repr(cfg.source if cfg.source else "0")
    out = repr(cfg.output_path) if cfg.output_path else "None"
    try:
        region = cfg.region_points if cfg.region_points.strip() else "[(20, 400), (1260, 400)]"
        if region.strip().startswith("{"):
            region_expr = region  # dict for RegionCounter
        else:
            region_expr = region
    except Exception:
        region_expr = "[(20, 400), (1260, 400)]"

    base = f'''
import sys
try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None  # type: ignore



def _require_cv2() -> None:
    if cv2 is None:
        raise ImportError("OpenCV (cv2) is required for this feature. Install with: pip install opencv-python")
from pathlib import Path

try:
    from ultralytics import solutions
except ImportError:
    print("pip install ultralytics")
    sys.exit(1)

source = {source}
model_path = {model}
output_path = {out}
cap = cv2.VideoCapture(source if source != "0" else 0)
if not cap.isOpened():
    print("Cannot open video source:", source)
    sys.exit(1)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
writer = None
if output_path:
    from pathlib import Path
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
'''
    stype = cfg.solution_type
    if stype == "DistanceCalculation":
        init = f'''
obj = solutions.DistanceCalculation(model=model_path, show=True)
'''
    elif stype == "Heatmap":
        cmap_name = cfg.colormap.replace("cv2.", "").strip() or "COLORMAP_JET"
        init = f'''
obj = solutions.Heatmap(model=model_path, show=True, colormap=getattr(cv2, {repr(cmap_name)}))
'''
    elif stype == "ObjectCounter":
        init = f'''
region = {region_expr}
obj = solutions.ObjectCounter(model=model_path, region=region, show=True)
'''
    elif stype == "RegionCounter":
        init = f'''
region = {region_expr}
obj = solutions.RegionCounter(model=model_path, region=region, show=True)
'''
    elif stype == "SpeedEstimator":
        init = f'''
obj = solutions.SpeedEstimator(model=model_path, fps={cfg.fps}, show=True)
'''
    elif stype == "TrackZone":
        init = f'''
region = {region_expr}
obj = solutions.TrackZone(model=model_path, region=region, show=True)
'''
    else:
        init = f'''
obj = solutions.ObjectCounter(model=model_path, show=True)
'''

    loop = '''
while cap.isOpened():
    ok, frame = cap.read()
    if not ok:
        break
    res = obj(frame)
    if writer is not None and res is not None and hasattr(res, "plot_im"):
        writer.write(res.plot_im)
    elif writer is not None and res is not None:
        writer.write(res)
cap.release()
if writer is not None:
    writer.release()
cv2.destroyAllWindows()
print("Done.")
'''
    return base + init + loop


def run_solution(
    cfg: SolutionsConfig,
    on_progress: Callable[[str], None] | None = None,
) -> None:
    """Generate script and run it in subprocess. Blocks until script exits."""
    if cfg.solution_type not in SOLUTION_TYPES:
        raise ValueError(f"Unknown solution type: {cfg.solution_type}")
    script = _script_content(cfg)
    if on_progress:
        on_progress("Запуск решения в отдельном процессе…")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(script)
        path = f.name
    try:
        subprocess.run([sys.executable, path], check=False)
    finally:
        Path(path).unlink(missing_ok=True)
    if on_progress:
        on_progress("Готово.")
