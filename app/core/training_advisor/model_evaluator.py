from __future__ import annotations

from pathlib import Path
from typing import Any


class ModelEvaluator:
    def evaluate(self, model_weights_path: Path, dataset_yaml: Path, out_dir: Path) -> dict[str, Any]:
        result: dict[str, Any] = {"warnings": [], "metrics": {}, "preview_images": []}
        if not model_weights_path.exists():
            return {"warnings": [f"weights not found: {model_weights_path}"], "metrics": {}, "preview_images": []}
        try:
            from ultralytics import YOLO

            model = YOLO(str(model_weights_path))
            val = model.val(data=str(dataset_yaml), imgsz=640, verbose=False)
            result["metrics"] = {
                "map50": float(getattr(getattr(val, "box", None), "map50", 0.0) or 0.0),
                "map": float(getattr(getattr(val, "box", None), "map", 0.0) or 0.0),
            }
            preds = model.predict(data=str(dataset_yaml), imgsz=640, max_det=20, save=True, project=str(out_dir), name="preview", verbose=False)
            for p in preds[:3]:
                save_dir = Path(getattr(p, "save_dir", out_dir / "preview"))
                for img in save_dir.rglob("*.jpg"):
                    result["preview_images"].append(str(img))
                    if len(result["preview_images"]) >= 3:
                        break
        except Exception as e:
            result["warnings"].append(f"model evaluation skipped: {e}")
        return result
