from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from PIL import Image


class DatasetInspector:
    def inspect(self, dataset_path: Path) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        stats: dict[str, Any] = {"images": 0, "labels": 0, "empty_labels": 0, "broken_images": 0}
        yaml_path = dataset_path if dataset_path.suffix in {".yaml", ".yml"} else dataset_path / "data.yaml"
        if not yaml_path.exists():
            return {"errors": [f"data.yaml not found: {yaml_path}"], "warnings": [], "statistics": stats}
        cfg = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        names = cfg.get("names", [])
        class_counter: Counter[int] = Counter()
        image_sizes: list[tuple[int, int]] = []
        for split in ("train", "val", "test"):
            rel = cfg.get(split)
            if not rel:
                continue
            base = yaml_path.parent
            images_dir = (base / rel).resolve()
            labels_dir = Path(str(images_dir).replace("images", "labels"))
            if not images_dir.exists() or not labels_dir.exists():
                warnings.append(f"{split}: images/labels folder missing")
                continue
            for img_path in images_dir.rglob("*.*"):
                if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
                    continue
                stats["images"] += 1
                try:
                    with Image.open(img_path) as im:
                        image_sizes.append(im.size)
                        im.verify()
                except Exception:
                    stats["broken_images"] += 1
                    errors.append(f"broken image: {img_path}")
                lbl = labels_dir / f"{img_path.stem}.txt"
                if not lbl.exists():
                    warnings.append(f"missing label: {lbl}")
                    continue
                stats["labels"] += 1
                lines = [ln.strip() for ln in lbl.read_text(encoding="utf-8").splitlines() if ln.strip()]
                if not lines:
                    stats["empty_labels"] += 1
                    continue
                for line in lines:
                    parts = line.split()
                    if len(parts) != 5:
                        errors.append(f"bad label format: {lbl}")
                        continue
                    cls_id = int(float(parts[0]))
                    class_counter[cls_id] += 1
                    vals = [float(v) for v in parts[1:]]
                    if any(v < 0 or v > 1 for v in vals):
                        errors.append(f"bbox out of range in {lbl}")
        if class_counter:
            counts = list(class_counter.values())
            if max(counts) / max(1, min(counts)) > 5:
                warnings.append("class imbalance detected (>5x)")
        if names and class_counter and max(class_counter) >= len(names):
            errors.append("class id is outside names[] range")
        avg_wh = [sum(x) / len(image_sizes) for x in zip(*image_sizes)] if image_sizes else [0, 0]
        stats["class_distribution"] = dict(class_counter)
        stats["mean_image_size"] = {"width": int(avg_wh[0]), "height": int(avg_wh[1])}
        return {"errors": errors, "warnings": warnings, "statistics": stats}
