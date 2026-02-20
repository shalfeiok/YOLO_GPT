"""
K-Fold Cross Validation: split dataset into K folds and optionally train on each.

Ref: https://docs.ultralytics.com/ru/guides/kfold-cross-validation/
Uses sklearn KFold, pandas, pyyaml. Creates train/val dirs and data.yaml per fold.
"""

from __future__ import annotations

import datetime
import random
import shutil
from collections import Counter
from pathlib import Path
from typing import Callable

import yaml

from app.features.kfold_integration.domain import KFoldConfig


SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png")


def run_kfold_split(
    cfg: KFoldConfig,
    on_progress: Callable[[str], None] | None = None,
) -> list[Path]:
    """
    Split dataset into K folds: create dirs, copy images/labels, write data.yaml per fold.
    Returns list of paths to dataset YAML files (one per fold).
    """
    dataset_path = Path(cfg.dataset_path)
    data_yaml_path = Path(cfg.data_yaml_path)
    k = cfg.k_folds
    random_state = cfg.random_state
    save_path = Path(cfg.output_path) if cfg.output_path else dataset_path / f"{datetime.date.today().isoformat()}_{k}-Fold_Cross-val"

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset path not found: {dataset_path}")
    if not data_yaml_path.exists():
        raise FileNotFoundError(f"Data YAML not found: {data_yaml_path}")

    def log(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    with open(data_yaml_path, encoding="utf-8") as f:
        data_yaml = yaml.safe_load(f)
    classes = data_yaml.get("names") or {}
    cls_idx = sorted(classes.keys())

    # Labels: doc uses dataset_path.rglob("*labels/*.txt"); support both flat and nested
    labels = sorted(dataset_path.rglob("*labels/*.txt"))
    if not labels:
        labels_dir = dataset_path / "labels"
        labels = sorted(labels_dir.rglob("*.txt")) if labels_dir.exists() else []
    if not labels:
        raise FileNotFoundError(f"No label files in {dataset_path} (expected *labels/*.txt or labels/*.txt)")

    try:
        import pandas as pd
        from sklearn.model_selection import KFold
    except ImportError as e:
        raise ImportError("K-Fold requires: pip install scikit-learn pandas pyyaml") from e

    index = [p.stem for p in labels]
    labels_df = pd.DataFrame([], columns=cls_idx, index=index)

    log("Building label vectors...")
    for label in labels:
        lbl_counter: Counter[int] = Counter()
        with open(label, encoding="utf-8") as lf:
            for line in lf:
                line = line.strip()
                if not line:
                    continue
                cls_id = int(line.split(" ", 1)[0])
                lbl_counter[cls_id] += 1
        labels_df.loc[label.stem] = pd.Series({i: lbl_counter.get(i, 0) for i in cls_idx})
    labels_df = labels_df.fillna(0.0)

    random.seed(0)  # for reproducibility (as in doc)
    kf = KFold(n_splits=k, shuffle=True, random_state=random_state)
    kfolds = list(kf.split(labels_df))

    folds = [f"split_{n}" for n in range(1, k + 1)]
    folds_df = pd.DataFrame(index=index, columns=folds)
    for i, (train_idx, val_idx) in enumerate(kfolds, start=1):
        folds_df[f"split_{i}"].loc[labels_df.iloc[train_idx].index] = "train"
        folds_df[f"split_{i}"].loc[labels_df.iloc[val_idx].index] = "val"

    # Распределение меток по фолдам: ratio val/train для каждого класса (как в доке)
    fold_lbl_distrb = pd.DataFrame(index=folds, columns=cls_idx)
    for n, (train_indices, val_indices) in enumerate(kfolds, start=1):
        train_totals = labels_df.iloc[train_indices].sum()
        val_totals = labels_df.iloc[val_indices].sum()
        ratio = val_totals / (train_totals + 1e-7)
        fold_lbl_distrb.loc[f"split_{n}"] = ratio

    save_path.mkdir(parents=True, exist_ok=True)
    ds_yamls: list[Path] = []

    for split in folds_df.columns:
        split_dir = save_path / split
        split_dir.mkdir(parents=True, exist_ok=True)
        (split_dir / "train" / "images").mkdir(parents=True, exist_ok=True)
        (split_dir / "train" / "labels").mkdir(parents=True, exist_ok=True)
        (split_dir / "val" / "images").mkdir(parents=True, exist_ok=True)
        (split_dir / "val" / "labels").mkdir(parents=True, exist_ok=True)
        dataset_yaml = split_dir / f"{split}_dataset.yaml"
        ds_yamls.append(dataset_yaml)
        with open(dataset_yaml, "w", encoding="utf-8") as ds_y:
            yaml.safe_dump(
                {
                    "path": split_dir.as_posix(),
                    "train": "train",
                    "val": "val",
                    "names": classes,
                },
                ds_y,
                allow_unicode=True,
            )

    images_dir = dataset_path / "images"
    images: list[Path] = []
    for ext in SUPPORTED_EXTENSIONS:
        images.extend(sorted((images_dir or dataset_path).rglob(f"*{ext}")))
    if not images:
        raise FileNotFoundError(f"No images in {images_dir or dataset_path}")

    stem_to_label: dict[str, Path] = {p.stem: p for p in labels}
    stem_to_image: dict[str, Path] = {p.stem: p for p in images}
    common_stems = [s for s in index if s in stem_to_image and s in stem_to_label]

    log("Copying files...")
    for idx, stem in enumerate(common_stems):
        if idx % 500 == 0 and idx:
            log(f"Copied {idx}/{len(common_stems)}...")
        image = stem_to_image[stem]
        label = stem_to_label[stem]
        for split, k_split in folds_df.loc[stem].items():
            img_to = save_path / split / k_split / "images"
            lbl_to = save_path / split / k_split / "labels"
            shutil.copy2(image, img_to / image.name)
            shutil.copy2(label, lbl_to / label.name)

    folds_df.to_csv(save_path / "kfold_datasplit.csv")
    fold_lbl_distrb.to_csv(save_path / "kfold_label_distribution.csv")
    log(f"K-Fold split saved to {save_path}; {len(ds_yamls)} dataset YAMLs.")
    return ds_yamls


def run_kfold_train(
    cfg: KFoldConfig,
    dataset_yaml_paths: list[Path],
    on_progress: Callable[[str], None] | None = None,
    console_queue=None,
) -> list[Path]:
    """
    Train YOLO on each fold; returns list of paths to best.pt per fold.
    Runs sequentially in current thread (call from worker thread if needed).
    """
    weights = cfg.weights_path or "yolo11n.pt"
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError("Ultralytics required: pip install ultralytics")

    results: list[Path] = []
    for k, dataset_yaml in enumerate(dataset_yaml_paths):
        if on_progress:
            on_progress(f"Training fold {k + 1}/{len(dataset_yaml_paths)}...")
        model = YOLO(weights, task="detect")
        train_result = model.train(
            data=str(dataset_yaml),
            epochs=cfg.train_epochs,
            batch=cfg.train_batch,
            project=cfg.train_project,
            name=f"fold_{k + 1}",
        )
        if hasattr(train_result, "save_dir"):
            best = Path(train_result.save_dir) / "weights" / "best.pt"
            if best.exists():
                results.append(best)
    return results
