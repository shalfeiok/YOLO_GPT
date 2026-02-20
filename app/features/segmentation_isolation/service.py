"""
Isolate segmentation objects: predict with seg model, create mask, save crops.

Ref: https://docs.ultralytics.com/ru/guides/isolating-segmentation-objects/
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable
try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None  # type: ignore



def _require_cv2() -> None:
    if cv2 is None:
        raise ImportError("OpenCV (cv2) is required for this feature. Install with: pip install opencv-python")
import numpy as np

from app.features.segmentation_isolation.domain import SegIsolationConfig


def run_seg_isolation(
    cfg: SegIsolationConfig,
    on_progress: Callable[[str], None] | None = None,
) -> int:
    """
    Run seg model on source (image or dir), isolate each detection (mask),
    save to output_dir. Returns number of saved images.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError("Ultralytics required: pip install ultralytics")

    if not cfg.model_path or not Path(cfg.model_path).exists():
        raise FileNotFoundError(f"Model not found: {cfg.model_path}")
    source = Path(cfg.source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source not found: {cfg.source_path}")
    out_dir = Path(cfg.output_dir) if cfg.output_dir else Path("runs/seg_isolation")
    out_dir.mkdir(parents=True, exist_ok=True)

    model = YOLO(cfg.model_path, task="segment")
    sources: list[Path] = []
    if source.is_file():
        sources = [source]
    else:
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp"):
            sources.extend(sorted(source.rglob(ext)))
    if not sources:
        raise FileNotFoundError(f"No images in {source}")

    saved = 0
    transparent = cfg.background == "transparent"
    crop = cfg.crop

    for idx, img_path in enumerate(sources):
        if on_progress:
            on_progress(f"Обработка {idx + 1}/{len(sources)}: {img_path.name}")
        results = model.predict(str(img_path), verbose=False)
        img = None
        for r in results:
            if img is None:
                img = np.copy(r.orig_img)
            img_name = Path(r.path).stem
            for ci, c in enumerate(r):
                if not hasattr(c, "masks") or c.masks is None:
                    continue
                try:
                    xy = c.masks.xy
                    if not xy:
                        continue
                    contour = np.array(xy.pop(), dtype=np.int32).reshape(-1, 1, 2)
                except (IndexError, AttributeError):
                    continue
                b_mask = np.zeros(img.shape[:2], np.uint8)
                cv2.drawContours(b_mask, [contour], -1, 255, cv2.FILLED)
                if transparent:
                    isolated = np.dstack([img, b_mask])
                else:
                    mask3ch = cv2.cvtColor(b_mask, cv2.COLOR_GRAY2BGR)
                    isolated = cv2.bitwise_and(mask3ch, img)
                if crop and hasattr(c, "boxes") and c.boxes is not None:
                    try:
                        xyxy = c.boxes.xyxy.cpu().numpy().squeeze()
                        x1, y1, x2, y2 = map(int, xyxy)
                        isolated = isolated[y1:y2, x1:x2]
                    except Exception:
                        import logging
                        logging.getLogger(__name__).debug('Optional segmentation isolation failed', exc_info=True)
                label = "unknown"
                if hasattr(c, "names") and c.names and hasattr(c.boxes, "cls"):
                    cls_list = c.boxes.cls.tolist()
                    if cls_list:
                        label = c.names.get(int(cls_list[0]), "unknown")
                out_name = f"{img_name}_{label}_{ci}.png"
                out_path = out_dir / out_name
                if isolated.ndim == 3 and isolated.shape[2] == 4:
                    cv2.imwrite(str(out_path), cv2.cvtColor(isolated, cv2.COLOR_RGBA2BGRA))
                else:
                    cv2.imwrite(str(out_path), isolated)
                saved += 1
    return saved
