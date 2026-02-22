from __future__ import annotations

import random
import shutil
from pathlib import Path

import yaml

from .common import (
    DEFAULT_VAL_RATIO,
    IMAGE_DIR_NAMES,
    IMAGE_EXTENSIONS,
    LABEL_DIR_NAMES,
    _split_label_line,
)


def _collect_image_paths(root: Path) -> list[Path]:
    """Собирает все изображения: в root, в папках с популярными именами (images/img/...) и в train/val/valid/test."""
    seen: set[Path] = set()
    root = root.resolve()

    def add_from_dir(directory: Path) -> None:
        if not directory.is_dir():
            return
        for ext in IMAGE_EXTENSIONS:
            for p in directory.glob(f"*{ext}"):
                if p.is_file():
                    seen.add(p.resolve())

    add_from_dir(root)
    for child in root.iterdir():
        if child.is_dir() and child.name.lower() in IMAGE_DIR_NAMES:
            add_from_dir(child)
        if child.is_dir() and child.name.lower() in ("train", "val", "valid", "test"):
            for sub in child.iterdir():
                if sub.is_dir() and sub.name.lower() in IMAGE_DIR_NAMES:
                    add_from_dir(sub)
            add_from_dir(child)

    if not seen:
        for child in root.iterdir():
            if child.is_dir():
                add_from_dir(child)

    return sorted(seen)


def _find_label_for_image(image_path: Path, root: Path) -> Path | None:
    """Ищет файл метки .txt для изображения: рядом с картинкой, в папках labels/annotations/ и т.д."""
    stem = image_path.stem
    root = root.resolve()
    next_to = image_path.parent / f"{stem}.txt"
    if next_to.is_file():
        return next_to

    for dir_name in LABEL_DIR_NAMES:
        d = root / dir_name
        if d.is_dir():
            lbl = d / f"{stem}.txt"
            if lbl.is_file():
                return lbl

    img_parent = image_path.parent
    for dir_name in LABEL_DIR_NAMES:
        d = img_parent.parent / dir_name if img_parent != root else root / dir_name
        if d.is_dir():
            lbl = d / f"{stem}.txt"
            if lbl.is_file():
                return lbl

    if img_parent != root:
        for dir_name in LABEL_DIR_NAMES:
            d = img_parent / dir_name
            if not d.is_dir():
                d = img_parent.parent / dir_name
            if d.is_dir():
                lbl = d / f"{stem}.txt"
                if lbl.is_file():
                    return lbl

    for child in root.iterdir():
        if child.is_dir() and child.name.lower() in LABEL_DIR_NAMES:
            lbl = child / f"{stem}.txt"
            if lbl.is_file():
                return lbl
        if child.is_dir() and child.name.lower() in ("train", "val", "valid", "test"):
            for sub in child.iterdir():
                if sub.is_dir() and sub.name.lower() in LABEL_DIR_NAMES:
                    lbl = sub / f"{stem}.txt"
                    if lbl.is_file():
                        return lbl
    return None


def _find_images_and_labels(root: Path) -> tuple[list[Path], list[Path | None]]:
    image_paths = _collect_image_paths(root)
    label_paths: list[Path | None] = [_find_label_for_image(img, root) for img in image_paths]
    return image_paths, label_paths


def prepare_for_yolo(
    source_dir: Path,
    output_dir: Path,
    val_ratio: float = DEFAULT_VAL_RATIO,
    seed: int | None = 42,
) -> Path:
    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    if seed is not None:
        random.seed(seed)

    image_paths, label_paths = _find_images_and_labels(source_dir)
    if not image_paths:
        raise FileNotFoundError(f"Не найдено изображений в {source_dir}")

    indices = list(range(len(image_paths)))
    random.shuffle(indices)
    n_val = max(1, int(len(indices) * val_ratio))
    val_indices = set(indices[:n_val])
    train_indices = set(indices[n_val:])

    for split, sub in (("train", "train"), ("val", "valid")):
        idx_set = train_indices if sub == "train" else val_indices
        out_images = output_dir / sub / "images"
        out_labels = output_dir / sub / "labels"
        out_images.mkdir(parents=True, exist_ok=True)
        out_labels.mkdir(parents=True, exist_ok=True)
        for i in idx_set:
            img = image_paths[i]
            shutil.copy2(img, out_images / img.name)
            lbl = label_paths[i]
            out_lbl_path = out_labels / (img.stem + ".txt")
            if lbl and lbl.exists():
                lines_out = []
                for line in lbl.read_text(encoding="utf-8").strip().splitlines():
                    parts = _split_label_line(line)
                    if len(parts) >= 5:
                        lines_out.append(f"{parts[0]} {parts[1]} {parts[2]} {parts[3]} {parts[4]}")
                out_lbl_path.write_text("\n".join(lines_out), encoding="utf-8")
            else:
                out_lbl_path.write_text("", encoding="utf-8")

    names: list[str] = []
    yaml_in_source = source_dir / "data.yaml"
    if yaml_in_source.exists():
        with open(yaml_in_source, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        n = data.get("nc", 0)
        raw_names = data.get("names")
        if isinstance(raw_names, list):
            names = list(raw_names)
        elif isinstance(raw_names, dict):
            names = [raw_names.get(i, f"class_{i}") for i in sorted(raw_names.keys())]
        if not names and n:
            names = [f"class_{i}" for i in range(n)]
    if not names:
        seen: set[int] = set()
        for lbl in label_paths:
            if lbl is None or not lbl.exists():
                continue
            for line in lbl.read_text(encoding="utf-8").strip().splitlines():
                parts = _split_label_line(line)
                if len(parts) >= 1:
                    try:
                        seen.add(int(parts[0]))
                    except ValueError:
                        continue
        nc = max(seen, default=0) + 1 if seen else 1
        names = [f"class_{i}" for i in range(nc)]

    data_yaml = {
        "path": str(output_dir),
        "train": "train/images",
        "val": "valid/images",
        "nc": len(names),
        "names": names,
    }
    yaml_path = output_dir / "data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_yaml, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return yaml_path
