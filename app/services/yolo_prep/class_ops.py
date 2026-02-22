from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from .common import IMAGE_EXTENSIONS, _split_label_line


def export_dataset_filter_classes(
    source_dataset_dir: Path,
    output_dataset_dir: Path,
    selected_class_indices: list[int],
    class_names: list[str],
) -> Path:
    source_dataset_dir = Path(source_dataset_dir).resolve()
    output_dataset_dir = Path(output_dataset_dir).resolve()
    if not selected_class_indices:
        raise ValueError("Не выбраны классы для экспорта")
    selected = sorted(set(selected_class_indices))
    old_to_new = {old: new for new, old in enumerate(selected)}
    new_names = [class_names[i] for i in selected if 0 <= i < len(class_names)]

    for split in ("train", "valid", "val"):
        src_imgs = source_dataset_dir / split / "images"
        src_lbls = source_dataset_dir / split / "labels"
        if not src_imgs.is_dir():
            continue
        dst_imgs = output_dataset_dir / split / "images"
        dst_lbls = output_dataset_dir / split / "labels"
        dst_imgs.mkdir(parents=True, exist_ok=True)
        dst_lbls.mkdir(parents=True, exist_ok=True)
        for img_path in src_imgs.iterdir():
            if img_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            lbl_path = src_lbls / (img_path.stem + ".txt")
            lines_out: list[str] = []
            if lbl_path.exists():
                for line in lbl_path.read_text(encoding="utf-8").strip().splitlines():
                    parts = _split_label_line(line)
                    if len(parts) < 5:
                        continue
                    try:
                        old_cid = int(parts[0])
                    except ValueError:
                        continue
                    if old_cid in old_to_new:
                        new_cid = old_to_new[old_cid]
                        lines_out.append(f"{new_cid} {parts[1]} {parts[2]} {parts[3]} {parts[4]}")
            if lines_out or not lbl_path.exists():
                shutil.copy2(img_path, dst_imgs / img_path.name)
                (dst_lbls / (img_path.stem + ".txt")).write_text(
                    "\n".join(lines_out), encoding="utf-8"
                )

    data_yaml = {
        "path": str(output_dataset_dir),
        "train": "train/images",
        "val": "valid/images",
        "nc": len(selected),
        "names": new_names,
    }
    yaml_path = output_dataset_dir / "data.yaml"
    output_dataset_dir.mkdir(parents=True, exist_ok=True)
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_yaml, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return yaml_path


def merge_classes_in_dataset(
    source_dataset_dir: Path,
    output_dataset_dir: Path,
    class_indices_to_merge: set[int],
    new_class_name: str,
    class_names: list[str],
) -> Path:
    source_dataset_dir = Path(source_dataset_dir).resolve()
    output_dataset_dir = Path(output_dataset_dir).resolve()
    if not class_indices_to_merge:
        raise ValueError("Выберите хотя бы один класс для объединения")
    merge_set = set(class_indices_to_merge)
    remaining = sorted(i for i in range(len(class_names)) if i not in merge_set)
    new_names = [new_class_name.strip() or "merged"] + [class_names[i] for i in remaining]
    old_to_new: dict[int, int] = {old: 0 for old in merge_set}
    for new_idx, old in enumerate(remaining, start=1):
        old_to_new[old] = new_idx

    for split in ("train", "valid", "val"):
        src_imgs = source_dataset_dir / split / "images"
        src_lbls = source_dataset_dir / split / "labels"
        if not src_imgs.is_dir():
            continue
        dst_imgs = output_dataset_dir / split / "images"
        dst_lbls = output_dataset_dir / split / "labels"
        dst_imgs.mkdir(parents=True, exist_ok=True)
        dst_lbls.mkdir(parents=True, exist_ok=True)
        for img_path in src_imgs.iterdir():
            if img_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            lbl_path = src_lbls / (img_path.stem + ".txt")
            lines_out = []
            if lbl_path.exists():
                for line in lbl_path.read_text(encoding="utf-8").strip().splitlines():
                    parts = _split_label_line(line)
                    if len(parts) < 5:
                        continue
                    try:
                        cid = int(parts[0])
                    except ValueError:
                        continue
                    if cid in old_to_new:
                        new_cid = old_to_new[cid]
                        lines_out.append(f"{new_cid} {parts[1]} {parts[2]} {parts[3]} {parts[4]}")
            if lines_out:
                shutil.copy2(img_path, dst_imgs / img_path.name)
                (dst_lbls / (img_path.stem + ".txt")).write_text(
                    "\n".join(lines_out), encoding="utf-8"
                )

    data_yaml = {
        "path": str(output_dataset_dir),
        "train": "train/images",
        "val": "valid/images",
        "nc": len(new_names),
        "names": new_names,
    }
    yaml_path = output_dataset_dir / "data.yaml"
    output_dataset_dir.mkdir(parents=True, exist_ok=True)
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_yaml, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return yaml_path


def rename_class_in_dataset(
    dataset_dir: Path,
    new_name: str,
    class_index: int | None = None,
    old_name: str | None = None,
) -> Path:
    dataset_dir = Path(dataset_dir).resolve()
    yaml_path = dataset_dir / "data.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Не найден {yaml_path}")
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    names = data.get("names")
    if isinstance(names, list):
        names = list(names)
    elif isinstance(names, dict):
        names = [names.get(i, f"class_{i}") for i in sorted(names.keys())]
    else:
        names = []
    if not names:
        raise ValueError("В data.yaml нет списка классов (names)")
    if class_index is not None:
        if class_index < 0 or class_index >= len(names):
            raise ValueError(f"Индекс класса {class_index} вне диапазона 0..{len(names) - 1}")
        idx = class_index
    elif old_name is not None:
        try:
            idx = names.index(old_name.strip())
        except ValueError as e:
            raise ValueError(f"Класс с именем «{old_name}» не найден") from e
    else:
        raise ValueError("Укажите class_index или old_name")
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("Новое имя не может быть пустым")
    names[idx] = new_name
    data["names"] = names
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return yaml_path
