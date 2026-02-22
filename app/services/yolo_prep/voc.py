from __future__ import annotations

from pathlib import Path

import yaml

from .common import _parse_voc_xml


def convert_voc_to_yolo(source_dir: Path) -> Path:
    """
    Конвертирует датасет Pascal VOC (XML_annotations, ids, images/train|val|test) в YOLO in-place.
    Создаёт labels/train, labels/val, labels/test и data.yaml в source_dir. Возвращает path к data.yaml.
    """
    root = Path(source_dir).resolve()
    xml_dir = root / "XML_annotations"
    ids_dir = root / "ids"
    labels_dir = root / "labels"
    if not xml_dir.is_dir() or not ids_dir.is_dir():
        raise FileNotFoundError(
            f"Ожидаются папки XML_annotations/ и ids/ в {root}. Выберите папку в формате Pascal VOC."
        )

    class_names: list[str] = []
    name_to_id: dict[str, int] = {}
    for xml_path in xml_dir.glob("*.xml"):
        try:
            _, _, objs = _parse_voc_xml(xml_path)
            for name, *_ in objs:
                if name not in name_to_id:
                    name_to_id[name] = len(class_names)
                    class_names.append(name)
        except Exception:
            continue
    if not class_names:
        class_names = ["Pedestrian"]
        name_to_id = {"Pedestrian": 0}

    for split in ("train", "val", "test"):
        ids_file = ids_dir / f"{split}.txt"
        if not ids_file.exists():
            continue
        image_ids = [
            line.strip()
            for line in ids_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        split_labels = labels_dir / split
        split_labels.mkdir(parents=True, exist_ok=True)
        for img_id in image_ids:
            xml_path = xml_dir / f"{img_id}.xml"
            if not xml_path.exists():
                (split_labels / f"{img_id}.txt").write_text("", encoding="utf-8")
                continue
            try:
                _, _, objs = _parse_voc_xml(xml_path)
            except Exception:
                (split_labels / f"{img_id}.txt").write_text("", encoding="utf-8")
                continue
            lines = []
            for name, xc, yc, wn, hn in objs:
                cid = name_to_id.get(name, 0)
                lines.append(f"{cid} {xc:.6f} {yc:.6f} {wn:.6f} {hn:.6f}")
            (split_labels / f"{img_id}.txt").write_text("\n".join(lines), encoding="utf-8")

    data = {
        "path": str(root),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": len(class_names),
        "names": class_names,
    }
    yaml_path = root / "data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return yaml_path
