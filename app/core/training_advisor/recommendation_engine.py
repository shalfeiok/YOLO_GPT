from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.core.training_advisor.models import RecommendationItem
from app.domain.training_config import TrainingConfig, diff_training_config


class RecommendationEngine:
    def recommend(
        self,
        current: TrainingConfig,
        dataset_health: dict[str, Any],
        run_summary: dict[str, Any],
        model_eval: dict[str, Any],
        mode: str = "Quick",
    ) -> tuple[TrainingConfig, list[RecommendationItem], list[dict[str, Any]], list[str]]:
        adv = dict(current.advanced_options or {})
        cfg = current
        items: list[RecommendationItem] = []
        warnings: list[str] = []

        def _set(param: str, new_val: Any, reason: str, confidence: float = 0.7) -> None:
            nonlocal cfg, adv
            old = cfg.to_dict()[param] if "." not in param else adv.get(param.split(".", 1)[1])
            if old == new_val:
                return
            if param.startswith("advanced_options."):
                adv[param.split(".", 1)[1]] = new_val
                cfg = replace(cfg, advanced_options=adv)
            else:
                cfg = replace(cfg, **{param: new_val})
            items.append(RecommendationItem(param=param, current=old, recommended=new_val, reason=reason, confidence=confidence))

        st = dataset_health.get("statistics", {})
        if dataset_health.get("errors"):
            _set("advanced_options.mosaic", 0.0, "Dataset has annotation errors; reduce aggressive augmentation", 0.8)
            _set("advanced_options.mixup", 0.0, "Dataset has annotation errors; reduce aggressive augmentation", 0.8)
        if st.get("empty_labels", 0) > 0:
            _set("advanced_options.cls", 0.7, "Many empty labels; increase classification loss weight", 0.6)
        if any("imbalance" in w for w in dataset_health.get("warnings", [])):
            _set("advanced_options.mixup", 0.15, "Class imbalance; mixup helps regularization", 0.65)
            _set("advanced_options.mosaic", 1.0, "Class imbalance; mosaic improves sample diversity", 0.6)
        mean_h = st.get("mean_image_size", {}).get("height", 0)
        if mean_h and mean_h > 900 and cfg.imgsz < 960:
            _set("imgsz", 960, "Large images/small objects likely; larger imgsz may improve recall", 0.7)

        metrics = run_summary.get("metrics", {})
        val_map = float(metrics.get("metrics/mAP50(B)", 0) or 0)
        train_loss = float(metrics.get("train/box_loss", 0) or 0)
        if val_map < 0.2 and train_loss > 0.5:
            _set("epochs", max(cfg.epochs, 120), "Underfitting signal from previous run", 0.7)
            _set("advanced_options.lr0", 0.005, "Lower lr can stabilize underfitting/noisy convergence", 0.6)
        if val_map < 0.2 and train_loss < 0.2:
            _set("advanced_options.mosaic", 0.3, "Possible overfitting; reduce aggressive augmentation tail", 0.6)
            _set("advanced_options.close_mosaic", 15, "Possible overfitting; close mosaic earlier", 0.65)

        if any("out of memory" in str(w).lower() for w in run_summary.get("warnings", [])):
            _set("batch", max(1, cfg.batch // 2) if cfg.batch > 1 else 1, "OOM in previous run", 0.9)
            _set("imgsz", max(640, cfg.imgsz - 128), "OOM in previous run", 0.8)
            _set("advanced_options.amp", False, "Disable AMP as fallback for unstable hardware/driver", 0.5)

        eval_map = float(model_eval.get("metrics", {}).get("map50", 0.0) or 0.0)
        if eval_map < 0.1:
            _set("patience", max(cfg.patience, 40), "Low validation quality, allow longer search before early stop", 0.6)

        if mode.lower() == "deep":
            warnings.append("Deep mode calibration uses lightweight heuristics in current build.")
            _set("workers", max(cfg.workers, 2), "Deep mode: improve throughput estimate", 0.5)

        return cfg, items, diff_training_config(current, cfg), warnings
