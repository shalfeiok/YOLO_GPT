"""Визуализация датасета: загрузка классов, изображения с bbox, фильтр по классам."""
from pathlib import Path
from typing import Optional
try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None  # type: ignore



def _require_cv2() -> None:
    if cv2 is None:
        raise ImportError("OpenCV (cv2) is required for this feature. Install with: pip install opencv-python")
import numpy as np
import yaml

# Цвета для классов (BGR)
_COLORS = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255),
    (0, 255, 255), (128, 0, 0), (0, 128, 0), (0, 0, 128), (128, 128, 0),
]


def load_classes_from_dataset(dataset_dir: Path) -> list[str]:
    """Загружает имена классов из data.yaml датасета."""
    data_yaml = Path(dataset_dir) / "data.yaml"
    if not data_yaml.exists():
        return []
    with open(data_yaml, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    names = data.get("names")
    if isinstance(names, list):
        return list(names)
    if isinstance(names, dict):
        return [names.get(i, f"class_{i}") for i in sorted(names.keys())]
    nc = int(data.get("nc", 0))
    return [f"class_{i}" for i in range(nc)]


def _find_labels_dir(dataset_dir: Path, image_path: Path) -> Optional[Path]:
    """Ищет папку labels для данного изображения (train/labels или val/labels)."""
    for split in ("train", "valid", "val"):
        labels_dir = dataset_dir / split / "labels"
        if labels_dir.is_dir():
            lbl = labels_dir / (image_path.stem + ".txt")
            if lbl.exists():
                return labels_dir
    if (dataset_dir / "labels").is_dir():
        return dataset_dir / "labels"
    return None


def read_yolo_labels(labels_path: Path, only_classes: Optional[set[int]] = None) -> list[tuple[int, float, float, float, float]]:
    """Читает YOLO label file. Возвращает [(class_id, x_center, y_center, w, h) normalized]."""
    if not labels_path.exists():
        return []
    out = []
    for line in labels_path.read_text(encoding="utf-8").strip().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        cid = int(parts[0])
        if only_classes is not None and cid not in only_classes:
            continue
        x, y, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
        out.append((cid, x, y, w, h))
    return out


def draw_boxes(
    img: np.ndarray,
    labels_path: Path,
    class_names: list[str],
    only_classes: Optional[set[int]] = None,
) -> np.ndarray:
    """Рисует bbox на изображении. img — BGR, метки в формате YOLO (normalized)."""
    img = img.copy()
    h, w = img.shape[:2]
    boxes = read_yolo_labels(labels_path, only_classes)
    for cid, xc, yc, bw, bh in boxes:
        x1 = int((xc - bw / 2) * w)
        y1 = int((yc - bh / 2) * h)
        x2 = int((xc + bw / 2) * w)
        y2 = int((yc + bh / 2) * h)
        color = _COLORS[cid % len(_COLORS)]
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        label = class_names[cid] if cid < len(class_names) else str(cid)
        cv2.putText(img, label, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    return img


def get_sample_image_path(dataset_dir: Path) -> Optional[Path]:
    """Возвращает путь к любому изображению из train или valid."""
    paths = get_sample_image_paths(dataset_dir, 1)
    return paths[0] if paths else None


def get_sample_image_paths(dataset_dir: Path, n: int = 6) -> list[Path]:
    """Возвращает до n путей к изображениям из train/valid (с приоритетом наличия меток)."""
    import random
    out: list[Path] = []
    for split in ("train", "valid", "val"):
        imgs_dir = dataset_dir / split / "images"
        labels_dir = dataset_dir / split / "labels"
        if not imgs_dir.is_dir():
            continue
        candidates: list[Path] = []
        for ext in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
            for p in imgs_dir.glob(f"*{ext}"):
                if labels_dir.is_dir() and (labels_dir / (p.stem + ".txt")).exists():
                    candidates.insert(0, p)
                else:
                    candidates.append(p)
        random.shuffle(candidates)
        for p in candidates:
            if p not in out:
                out.append(p)
                if len(out) >= n:
                    return out
    return out


def get_labels_path_for_image(dataset_dir: Path, image_path: Path) -> Optional[Path]:
    """Возвращает путь к .txt меткам для изображения."""
    stem = image_path.stem
    for split in ("train", "valid", "val"):
        labels_dir = dataset_dir / split / "labels"
        if labels_dir.is_dir():
            lbl = labels_dir / (stem + ".txt")
            if lbl.exists():
                return lbl
    return None
