from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from app.config import DEFAULT_BATCH, DEFAULT_EPOCHS, DEFAULT_IMGSZ, DEFAULT_PATIENCE
ADVANCED_DEFAULTS: dict[str, Any] = {
    "cache": False,
    "amp": True,
    "lr0": 0.01,
    "lrf": 0.01,
    "mosaic": 1.0,
    "mixup": 0.0,
    "close_mosaic": 10,
    "seed": 0,
    "fliplr": 0.5,
    "flipud": 0.0,
    "box": 7.5,
    "cls": 0.5,
    "dfl": 1.5,
    "degrees": 0.0,
    "translate": 0.1,
    "scale": 0.5,
    "shear": 0.0,
    "perspective": 0.0,
    "hsv_h": 0.015,
    "hsv_s": 0.7,
    "hsv_v": 0.4,
    "warmup_epochs": 3.0,
    "warmup_momentum": 0.8,
    "warmup_bias_lr": 0.1,
    "weight_decay": 0.0005,
}


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    model_name: str = "yolo11n.pt"
    weights_path: str | None = None
    dataset_paths: tuple[str, ...] = ()
    project: str = ""
    device: str = "cuda:0"
    epochs: int = DEFAULT_EPOCHS
    batch: int = DEFAULT_BATCH
    imgsz: int = DEFAULT_IMGSZ
    patience: int = DEFAULT_PATIENCE
    workers: int = 0
    optimizer: str = ""
    advanced_options: dict[str, Any] | None = None

    @classmethod
    def from_current_state(cls, state: dict[str, Any]) -> "TrainingConfig":
        adv = dict(ADVANCED_DEFAULTS)
        adv.update(dict(state.get("advanced_options") or {}))
        return cls(
            model_name=str(state.get("model_name") or "yolo11n.pt"),
            weights_path=state.get("weights_path"),
            dataset_paths=tuple(str(x) for x in (state.get("dataset_paths") or [])),
            project=str(state.get("project") or ""),
            device=str(state.get("device") or "cuda:0"),
            epochs=int(state.get("epochs", DEFAULT_EPOCHS)),
            batch=int(state.get("batch", DEFAULT_BATCH)),
            imgsz=int(state.get("imgsz", DEFAULT_IMGSZ)),
            patience=int(state.get("patience", DEFAULT_PATIENCE)),
            workers=int(state.get("workers", 0)),
            optimizer=str(state.get("optimizer") or ""),
            advanced_options=adv,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.epochs < 1:
            errors.append("epochs must be >= 1")
        if self.batch < -1:
            errors.append("batch must be >= -1")
        if not (64 <= self.imgsz <= 2048):
            errors.append("imgsz must be in [64, 2048]")
        if self.patience < 1:
            errors.append("patience must be >= 1")
        if not (0 <= self.workers <= 32):
            errors.append("workers must be in [0, 32]")
        adv = self.advanced_options or {}
        for key in ADVANCED_DEFAULTS:
            if key not in adv:
                errors.append(f"advanced option is missing: {key}")
        return errors


def diff_training_config(current: TrainingConfig, recommended: TrainingConfig) -> list[dict[str, Any]]:
    left = current.to_dict()
    right = recommended.to_dict()
    result: list[dict[str, Any]] = []
    for key in sorted(left):
        if left[key] == right[key]:
            continue
        if key == "advanced_options":
            l_adv = left[key] or {}
            r_adv = right[key] or {}
            for adv_key in sorted(set(l_adv) | set(r_adv)):
                if l_adv.get(adv_key) != r_adv.get(adv_key):
                    result.append(
                        {"param": f"advanced_options.{adv_key}", "current": l_adv.get(adv_key), "recommended": r_adv.get(adv_key)}
                    )
            continue
        result.append({"param": key, "current": left[key], "recommended": right[key]})
    return result


def export_training_config(path: Path, cfg: TrainingConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        import json

        path.write_text(json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return
    path.write_text(cfg.to_yaml(), encoding="utf-8")
