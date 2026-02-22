"""Приведение папки с изображениями и метками к формату YOLO (train/val, data.yaml). Поддержка Pascal VOC (XML)."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path



def _split_label_line(line: str) -> list[str]:
    """Разбивает строку метки по пробелам и запятым (поддержка CSV-формата)."""
    line = line.strip()
    if not line:
        return []
    return [t for t in re.split(r"[\s,]+", line) if t]


# Расширения изображений
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
# Доля валидации по умолчанию
DEFAULT_VAL_RATIO = 0.2

# Популярные названия папок с изображениями (для гибкого поиска датасетов)
IMAGE_DIR_NAMES = frozenset(
    {
        "images",
        "img",
        "imgs",
        "image",
        "photos",
        "pics",
        "jpg",
        "jpeg",
        "data",
        "train",
        "val",
        "valid",
        "test",
        "train_images",
        "val_images",
        "test_images",
        "картинки",
        "изображения",
        "фото",
        "данные",
    }
)

# Популярные названия папок с метками (YOLO .txt или разметка)
LABEL_DIR_NAMES = frozenset(
    {
        "labels",
        "label",
        "annotations",
        "annotation",
        "ann",
        "lbl",
        "lbls",
        "yolo_labels",
        "yolo",
        "txt",
        "ground_truth",
        "gt",
        "метки",
        "разметка",
        "аннотации",
        "labels_train",
        "labels_val",
        "labels_test",
    }
)


def is_voc_dataset(root: Path) -> bool:
    """Проверяет, что папка — датасет Pascal VOC: XML_annotations/, ids/*.txt, images/train|val|test."""
    root = Path(root).resolve()
    if not (root / "XML_annotations").is_dir():
        return False
    ids_dir = root / "ids"
    if not ids_dir.is_dir():
        return False
    if not any((ids_dir / f).exists() for f in ("train.txt", "val.txt", "test.txt")):
        return False
    images = root / "images"
    return images.is_dir() and any((images / s).is_dir() for s in ("train", "val", "test"))


def _parse_voc_xml(
    xml_path: Path,
) -> tuple[int, int, list[tuple[str, float, float, float, float]]]:
    """Парсит VOC XML. Возвращает (width, height, [(class_name, x_center_norm, y_center_norm, w_norm, h_norm), ...])."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    size = root.find("size")
    if size is None:
        raise ValueError(f"No size in {xml_path}")
    w_el, h_el = size.find("width"), size.find("height")
    if w_el is None or h_el is None or w_el.text is None or h_el.text is None:
        raise ValueError(f"Invalid size in {xml_path}")
    w, h = int(w_el.text), int(h_el.text)
    if w <= 0 or h <= 0:
        raise ValueError(f"Invalid size in {xml_path}: {w}x{h}")
    objects: list[tuple[str, float, float, float, float]] = []
    for obj in root.findall("object"):
        name_el = obj.find("name")
        if name_el is None or name_el.text is None:
            continue
        name = name_el.text.strip()
        bnd = obj.find("bndbox")
        if bnd is None:
            continue

        def _f(tag: str) -> float:
            el = bnd.find(tag)
            if el is None or el.text is None:
                return 0.0
            try:
                return float(el.text)
            except ValueError:
                return 0.0

        xmin = _f("xmin")
        ymin = _f("ymin")
        xmax = _f("xmax")
        ymax = _f("ymax")
        x_center = (xmin + xmax) / 2.0 / w
        y_center = (ymin + ymax) / 2.0 / h
        width_norm = (xmax - xmin) / w
        height_norm = (ymax - ymin) / h
        objects.append((name, x_center, y_center, width_norm, height_norm))
    return w, h, objects
