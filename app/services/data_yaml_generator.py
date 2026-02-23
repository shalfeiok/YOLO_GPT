from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
_LIST_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "train": (re.compile(r"^train.*list$", re.I),),
    "val": (re.compile(r"^(val|valid).*list$", re.I),),
    "test": (re.compile(r"^test.*list$", re.I),),
}


@dataclass(slots=True)
class DataYamlBuildResult:
    data_yaml_path: Path
    splits: dict[str, str | list[str]]
    names: list[str]
    names_source: str
    warnings: list[str]


def generate_data_yaml(dataset_root: Path) -> DataYamlBuildResult:
    root = Path(dataset_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Dataset root not found: {root}")

    warnings: list[str] = []
    splits = _detect_splits(root, warnings)
    names, names_source, names_warnings = _detect_names(root)
    warnings.extend(names_warnings)

    payload: dict[str, Any] = {
        "nc": len(names),
        "names": names,
    }
    for key in ("train", "val", "test"):
        if key in splits:
            payload[key] = splits[key]

    data_yaml_path = root / "data.yaml"
    if data_yaml_path.exists():
        shutil.copy2(data_yaml_path, data_yaml_path.with_suffix(".yaml.bak"))

    with data_yaml_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, allow_unicode=True, sort_keys=False, default_flow_style=False, indent=2)

    return DataYamlBuildResult(
        data_yaml_path=data_yaml_path,
        splits=splits,
        names=names,
        names_source=names_source,
        warnings=warnings,
    )


def _detect_splits(root: Path, warnings: list[str]) -> dict[str, str | list[str]]:
    list_files = {p.stem.lower(): p for p in root.glob("*list.txt") if p.is_file()}
    if list_files:
        out: dict[str, str | list[str]] = {}
        for split, patterns in _LIST_PATTERNS.items():
            for stem, path in list_files.items():
                if any(pat.match(stem) for pat in patterns):
                    out[split] = _rel(path, root)
                    break
        if "val" not in out:
            warnings.append("split 'val' not found")
        return out

    out: dict[str, str | list[str]] = {}
    tests: list[str] = []

    for split_dir in sorted([d for d in root.iterdir() if d.is_dir()], key=lambda p: p.name.lower()):
        split_name = split_dir.name.lower()
        images_root = _detect_images_root(split_dir)
        if images_root is None:
            if split_name.startswith("test"):
                warnings.append(f"split contains no images, skipped: {split_dir.name}")
            continue

        rel_path = _rel(images_root, root)
        if split_name.startswith("train") and "train" not in out:
            out["train"] = rel_path
        elif split_name.startswith(("val", "valid")) and "val" not in out:
            out["val"] = rel_path
        elif split_name.startswith("test"):
            tests.append(rel_path)

    if tests:
        out["test"] = tests if len(tests) > 1 else tests[0]
    if "val" not in out:
        warnings.append("split 'val' not found")
    return out


def _detect_images_root(split_dir: Path) -> Path | None:
    for preferred in ("images", "sequences"):
        candidate = split_dir / preferred
        if candidate.is_dir() and _count_images(candidate) > 0:
            return candidate

    best: Path | None = None
    best_count = 0
    for child in [p for p in split_dir.iterdir() if p.is_dir()]:
        count = _count_images(child)
        if count > best_count:
            best = child
            best_count = count
    return best


def _detect_names(root: Path) -> tuple[list[str], str, list[str]]:
    warnings: list[str] = []

    for yaml_name in ("data.yaml", "dataset.yaml"):
        yaml_path = root / yaml_name
        if yaml_path.exists():
            data = _load_yaml(yaml_path)
            names = _extract_names(data)
            if names:
                return names, f"{yaml_name}:names", warnings

    for txt_name in ("classes.txt", "names.txt", "obj.names"):
        txt_path = root / txt_name
        if txt_path.exists():
            names = [line.strip() for line in txt_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if names:
                return names, txt_name, warnings

    max_class_id = _infer_max_class_id_from_labels(root)
    if max_class_id is not None:
        warnings.append("names were inferred from labels: generated placeholder classes")
        names = [f"class{i}" for i in range(max_class_id + 1)]
        return names, "labels_inference", warnings

    warnings.append("names source not found: fallback to ['class0']")
    return ["class0"], "fallback_default", warnings


def _infer_max_class_id_from_labels(root: Path) -> int | None:
    candidates = [d for d in root.rglob("*") if d.is_dir() and d.name.lower() == "labels"]
    txt_files: list[Path] = []
    for labels_dir in candidates:
        txt_files.extend([p for p in labels_dir.rglob("*.txt") if p.is_file()])
    if not txt_files:
        txt_files = [p for p in root.glob("*.txt") if p.is_file() and p.name.lower() not in {"trainlist.txt", "vallist.txt", "testlist.txt", "classes.txt", "names.txt", "obj.names"}]

    max_id: int | None = None
    for txt_path in txt_files:
        for raw_line in txt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            if not parts[0].isdigit():
                continue
            if not _looks_like_yolo_row(parts[1:5]):
                continue
            cls_id = int(parts[0])
            max_id = cls_id if max_id is None else max(max_id, cls_id)
    return max_id


def _looks_like_yolo_row(values: list[str]) -> bool:
    try:
        nums = [float(v) for v in values]
    except ValueError:
        return False
    return all(0.0 <= n <= 1.0 for n in nums)


def _extract_names(data: dict[str, Any]) -> list[str]:
    names = data.get("names")
    if isinstance(names, list):
        return [str(x) for x in names]
    if isinstance(names, dict):
        items = sorted(names.items(), key=lambda item: int(item[0]))
        return [str(v) for _, v in items]
    return []


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data if isinstance(data, dict) else {}


def _count_images(path: Path) -> int:
    return sum(1 for p in path.rglob("*") if p.is_file() and p.suffix.lower() in _IMAGE_EXTS)


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()
