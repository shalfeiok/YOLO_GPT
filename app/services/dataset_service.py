"""Сборка объединённого data.yaml из одного или нескольких датасетов (SOLID: единственная ответственность)."""
from pathlib import Path
from typing import Any, List, Optional

import yaml

from app.interfaces import IDatasetConfigBuilder


def _find_images_dir(base: Path, candidates: tuple[str, ...]) -> Optional[Path]:
    for name in candidates:
        p = base / name / "images"
        if p.is_dir():
            return p.resolve()
    return None


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _normalize_names(data: dict) -> list[str]:
    names = data.get("names")
    if names is None:
        return []
    if isinstance(names, list):
        return list(names)
    if isinstance(names, dict):
        return [names.get(i, f"class_{i}") for i in sorted(names.keys())]
    return []


class DatasetConfigBuilder(IDatasetConfigBuilder):
    """Формирует один data.yaml с путями train/val из нескольких датасетов; объединяет nc и names."""

    TRAIN_DIRS = ("train",)
    VALID_DIRS = ("valid", "val")
    TEST_DIRS = ("test", "test-dev")

    def build_multi(self, dataset_paths: List[Path], output_yaml: Path) -> Path:
        """Объединяет несколько датасетов в один data.yaml. nc = max по всем, names объединяются."""
        if not dataset_paths:
            raise ValueError("Нужен хотя бы один датасет")
        bases = [Path(p).resolve() for p in dataset_paths]
        out = Path(output_yaml).resolve()

        all_data = []
        for b in bases:
            all_data.append(_load_yaml(b / "data.yaml") if (b / "data.yaml").exists() else {})

        nc = max(int(d.get("nc", 0)) for d in all_data) if all_data else 1
        nc = max(nc, 1)
        names_by_idx: dict[int, str] = {}
        for data in all_data:
            nlist = _normalize_names(data)
            for i, name in enumerate(nlist):
                if i not in names_by_idx:
                    names_by_idx[i] = name
        names = [names_by_idx.get(i, f"class_{i}") for i in range(nc)]
        if not names:
            names = [f"class_{i}" for i in range(nc)]

        train_paths: list[str] = []
        val_paths: list[str] = []

        for i, base in enumerate(bases):
            data = all_data[i] if i < len(all_data) else {}
            # Поддержка data.yaml с путями вида images/train, images/val (VOC и Ultralytics)
            train_key = data.get("train")
            val_key = data.get("val")
            if train_key:
                train_dir = (base / train_key) if not Path(train_key).is_absolute() else Path(train_key)
                if train_dir.is_dir():
                    train_paths.append(str(train_dir.resolve()))
                    if val_key:
                        val_dir = (base / val_key) if not Path(val_key).is_absolute() else Path(val_key)
                        if val_dir.is_dir():
                            val_paths.append(str(val_dir.resolve()))
                    else:
                        for folder in self.VALID_DIRS:
                            imgs = _find_images_dir(base, (folder,))
                            if imgs:
                                val_paths.append(str(imgs))
                                break
                    continue
            # Классическая структура: train/images, valid/images
            for folder in self.TRAIN_DIRS:
                imgs = _find_images_dir(base, (folder,))
                if imgs:
                    train_paths.append(str(imgs))
                    break
            for folder in self.VALID_DIRS:
                imgs = _find_images_dir(base, (folder,))
                if imgs:
                    val_paths.append(str(imgs))
                    break

        if not train_paths:
            raise FileNotFoundError(
                f"Не найдено папок с изображениями для обучения в {bases}. "
                "Ожидается: train/images или images/train, и valid/images или images/val (и data.yaml)."
            )
        # Ultralytics требует непустой val; если valid/val нет — используем train для val
        if not val_paths:
            val_paths = list(train_paths)

        config: dict[str, Any] = {
            "path": str(out.parent),
            "train": train_paths[0] if len(train_paths) == 1 else train_paths,
            "val": val_paths[0] if len(val_paths) == 1 else val_paths,
            "nc": nc,
            "names": names,
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return out

    def build(
        self,
        dataset1_path: Path,
        dataset2_path: Path,
        output_yaml: Path,
        primary_yaml: Optional[Path] = None,
    ) -> Path:
        return self.build_multi([dataset1_path, dataset2_path], output_yaml)
