"""Приведение папки с изображениями и метками к формату YOLO (train/val, data.yaml). Поддержка Pascal VOC (XML)."""
import re
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import yaml


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
IMAGE_DIR_NAMES = frozenset({
    "images", "img", "imgs", "image", "photos", "pics", "jpg", "jpeg", "data",
    "train", "val", "valid", "test", "train_images", "val_images", "test_images",
    "картинки", "изображения", "фото", "данные",
})

# Популярные названия папок с метками (YOLO .txt или разметка)
LABEL_DIR_NAMES = frozenset({
    "labels", "label", "annotations", "annotation", "ann", "lbl", "lbls",
    "yolo_labels", "yolo", "txt", "ground_truth", "gt",
    "метки", "разметка", "аннотации", "labels_train", "labels_val", "labels_test",
})


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


def convert_voc_to_yolo(source_dir: Path) -> Path:
    """
    Конвертирует датасет Pascal VOC (XML_annotations, ids, images/train|val|test) в YOLO in-place.
    Создаёт labels/train, labels/val, labels/test и data.yaml в source_dir. Возвращает path к data.yaml.
    """
    root = Path(source_dir).resolve()
    xml_dir = root / "XML_annotations"
    ids_dir = root / "ids"
    images_dir = root / "images"
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

    # 1) Прямо в корне
    add_from_dir(root)

    # 2) Прямые подпапки с «картинными» именами
    for child in root.iterdir():
        if child.is_dir() and child.name.lower() in IMAGE_DIR_NAMES:
            add_from_dir(child)
        # 3) Вложенная структура train/images, val/images и т.д.
        if child.is_dir() and child.name.lower() in ("train", "val", "valid", "test"):
            for sub in child.iterdir():
                if sub.is_dir() and sub.name.lower() in IMAGE_DIR_NAMES:
                    add_from_dir(sub)
            add_from_dir(child)

    # 4) Любая подпапка первого уровня (датасет типа project/photos/...)
    if not seen:
        for child in root.iterdir():
            if child.is_dir():
                add_from_dir(child)

    return sorted(seen)


def _find_label_for_image(image_path: Path, root: Path) -> Optional[Path]:
    """Ищет файл метки .txt для изображения: рядом с картинкой, в папках labels/annotations/ и т.д."""
    stem = image_path.stem
    root = root.resolve()

    # 1) Рядом с изображением
    next_to = image_path.parent / f"{stem}.txt"
    if next_to.is_file():
        return next_to

    # 2) Папки с метками в корне датасета
    for dir_name in LABEL_DIR_NAMES:
        d = root / dir_name
        if d.is_dir():
            lbl = d / f"{stem}.txt"
            if lbl.is_file():
                return lbl

    # 3) Тот же путь, что и картинка, но папка с «меточным» именем (например images/ -> labels/)
    img_parent = image_path.parent
    for dir_name in LABEL_DIR_NAMES:
        # labels рядом с папкой images
        d = img_parent.parent / dir_name if img_parent != root else root / dir_name
        if d.is_dir():
            lbl = d / f"{stem}.txt"
            if lbl.is_file():
                return lbl

    # 4) В той же подпапке, что и картинка (train/labels при train/images)
    if img_parent != root:
        for dir_name in LABEL_DIR_NAMES:
            d = img_parent / dir_name
            if not d.is_dir():
                d = img_parent.parent / dir_name
            if d.is_dir():
                lbl = d / f"{stem}.txt"
                if lbl.is_file():
                    return lbl

    # 5) Рекурсивный поиск по одной папке с «меточным» именем (annotations/...)
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


def _find_images_and_labels(
    root: Path,
) -> tuple[list[Path], list[Optional[Path]]]:
    """Ищет изображения по популярным названиям папок; для каждой картинки ищет метку в логичных местах."""
    image_paths = _collect_image_paths(root)
    label_paths: list[Optional[Path]] = [_find_label_for_image(img, root) for img in image_paths]
    return image_paths, label_paths


def prepare_for_yolo(
    source_dir: Path,
    output_dir: Path,
    val_ratio: float = DEFAULT_VAL_RATIO,
    seed: Optional[int] = 42,
) -> Path:
    """
    Создаёт в output_dir структуру YOLO: train/images, train/labels, val/images, val/labels, data.yaml.
    source_dir — папка с изображениями (и опционально labels/ или те же имена .txt).
    """
    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    if seed is not None:
        random.seed(seed)

    image_paths, label_paths = _find_images_and_labels(source_dir)
    if not image_paths:
        raise FileNotFoundError(f"Не найдено изображений в {source_dir}")

    # Разбивка train/val
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
                # Нормализуем в формат YOLO (пробелы): поддерживаем исходные метки с запятыми
                lines_out = []
                for line in lbl.read_text(encoding="utf-8").strip().splitlines():
                    parts = _split_label_line(line)
                    if len(parts) >= 5:
                        lines_out.append(f"{parts[0]} {parts[1]} {parts[2]} {parts[3]} {parts[4]}")
                out_lbl_path.write_text("\n".join(lines_out), encoding="utf-8")
            else:
                out_lbl_path.write_text("", encoding="utf-8")

    # Имена классов: по умолчанию из первого попавшегося data.yaml или class_0, class_1, ...
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
        # Собираем уникальные class_id из меток (поддержка строк с запятыми)
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

    nc = len(names)
    data_yaml = {
        "path": str(output_dir),
        "train": "train/images",
        "val": "valid/images",
        "nc": nc,
        "names": names,
    }
    yaml_path = output_dir / "data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_yaml, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return yaml_path


def export_dataset_filter_classes(
    source_dataset_dir: Path,
    output_dataset_dir: Path,
    class_indices: set[int],
    class_names: list[str],
) -> Path:
    """
    Копирует датасет в output_dataset_dir, оставляя только выбранные классы.
    class_indices — индексы классов (0-based). В новых метках классы перенумерованы 0, 1, 2, ...
    """
    import shutil
    source_dataset_dir = Path(source_dataset_dir).resolve()
    output_dataset_dir = Path(output_dataset_dir).resolve()
    if not class_indices:
        raise ValueError("Выберите хотя бы один класс")
    sorted_ids = sorted(class_indices)
    old_to_new: dict[int, int] = {old: i for i, old in enumerate(sorted_ids)}
    new_names = [class_names[i] for i in sorted_ids if i < len(class_names)]
    if len(new_names) < len(sorted_ids):
        new_names.extend(f"class_{i}" for i in range(len(new_names), len(sorted_ids)))

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
            if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
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
            if lines_out or not lbl_path.exists():
                shutil.copy2(img_path, dst_imgs / img_path.name)
                (dst_lbls / (img_path.stem + ".txt")).write_text("\n".join(lines_out), encoding="utf-8")

    data_yaml = {
        "path": str(output_dataset_dir),
        "train": "train/images",
        "val": "valid/images",
        "nc": len(sorted_ids),
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
    """
    Создаёт датасет в output_dataset_dir, объединяя выбранные классы в один с именем new_class_name.
    class_indices_to_merge — индексы классов (0-based), которые объединяются в один.
    Остальные классы сохраняются и перенумеровываются: объединённый класс = 0, остальные по порядку.
    """
    source_dataset_dir = Path(source_dataset_dir).resolve()
    output_dataset_dir = Path(output_dataset_dir).resolve()
    if not class_indices_to_merge:
        raise ValueError("Выберите хотя бы один класс для объединения")
    merge_set = set(class_indices_to_merge)
    remaining = sorted(i for i in range(len(class_names)) if i not in merge_set)
    new_names = [new_class_name.strip() or "merged"] + [class_names[i] for i in remaining]
    old_to_new: dict[int, int] = {}
    for old in merge_set:
        old_to_new[old] = 0
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
            if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
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
                (dst_lbls / (img_path.stem + ".txt")).write_text("\n".join(lines_out), encoding="utf-8")

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
    class_index: Optional[int] = None,
    old_name: Optional[str] = None,
) -> Path:
    """
    Переименовывает один класс в data.yaml датасета.
    Указывают либо class_index (0-based), либо old_name (текущее имя). new_name — новое имя.
    Файлы меток не меняются (индексы классов остаются те же).
    """
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
        except ValueError:
            raise ValueError(f"Класс с именем «{old_name}» не найден")
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
