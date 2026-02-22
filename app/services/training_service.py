#commit и версия
"""Обучение YOLO в фоновом потоке с прогрессом и выводом в консоль (SOLID: единственная ответственность).

Учитывает конфиг интеграций: Albumentations (augmentations), Comet ML (env).
"""

import logging
from collections.abc import Callable
from pathlib import Path
from queue import Queue
from threading import Event
from typing import Any

from app.console_redirect import (
    redirect_stdout_stderr_to_queue,
    restore_stdout_stderr,
)
from app.device_utils import PYTORCH_NIGHTLY_HINT
from app.exceptions import StopTrainingRequested
from app.interfaces import ITrainer

log = logging.getLogger(__name__)


class TrainingService(ITrainer):
    """Сервис обучения Ultralytics YOLO.

    Сервис **не** управляет потоками: обучение выполняется синхронно.
    Поток/асинхронность — ответственность слоя приложения/VM (например, TrainingViewModel).
    """

    def __init__(self) -> None:
        self._stop_requested = Event()

    def train(
        self,
        *,
        data_yaml: Path,
        model_name: str,
        epochs: int,
        batch: int,
        imgsz: int,
        device: str,
        patience: int,
        project: Path,
        on_progress: Callable[[float, str], None] | None = None,
        console_queue: Queue | None = None,
        weights_path: Path | None = None,
        workers: int = 0,
        optimizer: str = "",
        advanced_options: dict | None = None,
    ) -> Path | None:
        """Запускает обучение синхронно; возвращает путь к best.pt по завершении.

        Использует конфиг интеграций (Albumentations, Comet). Для UI-консоли может писать строки в очередь.
        """
        self._stop_requested.clear()
        result_holder: list[Path] = []
        cancelled = False

        # Redirect stdout/stderr so full Ultralytics print() output (epoch progress, metrics) reaches UI console and is parsed for metrics
        old_out, old_err = None, None
        if console_queue is not None:
            old_out, old_err = redirect_stdout_stderr_to_queue(
                console_queue, also_keep_original=False
            )

        # Интеграции: Comet ML (env), Albumentations (augmentations) — настройки из вкладок «Интеграции» и «Обучение»
        comet_prev: dict = {}
        augmentations_list: list = []
        try:
            from app.features.albumentations_integration.domain import AlbumentationsConfig
            from app.features.albumentations_integration.service import (
                get_albumentations_transforms,
            )
            from app.features.comet_integration.domain import CometConfig
            from app.features.comet_integration.service import apply_comet_env
            from app.features.integrations_config import load_config

            config = load_config()
            comet_cfg = CometConfig.from_dict(config.get("comet", {}))
            comet_prev = apply_comet_env(comet_cfg)
            albu_cfg = AlbumentationsConfig.from_dict(config.get("albumentations", {}))
            augmentations_list = get_albumentations_transforms(albu_cfg)
        except Exception:
            log.exception("Failed to apply integrations configuration; continuing with defaults")

        try:
            from ultralytics import YOLO

            load_path = str(weights_path) if weights_path and weights_path.exists() else model_name
            model = YOLO(load_path)
            project.mkdir(parents=True, exist_ok=True)

            def on_epoch_end(trainer: Any) -> None:
                if self._stop_requested.is_set():
                    raise StopTrainingRequested("Остановка по запросу пользователя")
                if on_progress and getattr(trainer, "epochs", None):
                    total = trainer.epochs
                    current = getattr(trainer, "epoch", 0) + 1
                    on_progress(current / total, f"Epoch {current}/{total}")

            model.add_callback("on_train_epoch_end", on_epoch_end)

            train_device = None  # auto = prefer GPU
            if device and device.strip().lower() == "cpu":
                train_device = "cpu"

            data_path = str(data_yaml)
            train_kw: dict = {
                "data": data_path,
                "epochs": epochs,
                "batch": batch,
                "imgsz": imgsz,
                "device": train_device,
                "patience": patience,
                "project": str(project),
                "exist_ok": True,
                "verbose": True,
                "workers": workers,
            }
            if optimizer and optimizer.strip():
                train_kw["optimizer"] = optimizer.strip()
            # Передаём кастомные augmentations только если они настроены,
            # иначе сохраняем встроенные аугментации Ultralytics по умолчанию.
            if augmentations_list:
                train_kw["augmentations"] = augmentations_list
            # Расширенные настройки из диалога (cache, lr0, lrf, mosaic, mixup, seed, box, cls, dfl и др.)
            if advanced_options:
                ignored_advanced_options: list[str] = []
                for k, v in advanced_options.items():
                    if k in (
                        "cache",
                        "amp",
                        "lr0",
                        "lrf",
                        "mosaic",
                        "mixup",
                        "close_mosaic",
                        "seed",
                        "fliplr",
                        "flipud",
                        "box",
                        "cls",
                        "dfl",
                        "degrees",
                        "translate",
                        "scale",
                        "shear",
                        "perspective",
                        "hsv_h",
                        "hsv_s",
                        "hsv_v",
                        "warmup_epochs",
                        "warmup_momentum",
                        "warmup_bias_lr",
                        "weight_decay",
                    ):
                        train_kw[k] = v
                    else:
                        ignored_advanced_options.append(str(k))
                if ignored_advanced_options:
                    log.warning(
                        "Unknown advanced training options were ignored: %s",
                        ", ".join(sorted(ignored_advanced_options)),
                    )
            # При cache=True на Windows spawn воркеров приводит к сериализации кэша в память → MemoryError.
            # Загрузка из кэша в одном процессе (workers=0) стабильна и быстра.
            if train_kw.get("cache"):
                train_kw["workers"] = 0

            try:
                results = model.train(**train_kw)
            except RuntimeError as e:
                err_msg = str(e)
                if "no kernel image is available" in err_msg or "CUDA" in err_msg:
                    if console_queue is not None:
                        console_queue.put(f"[Fallback] GPU не совместим: {err_msg[:200]}")
                        console_queue.put(f"[Fallback] {PYTORCH_NIGHTLY_HINT}")
                        console_queue.put("[Fallback] Продолжаем на CPU…")
                    if on_progress:
                        on_progress(0, "Переход на CPU (GPU не совместим)…")
                    model = YOLO(load_path)
                    model.add_callback("on_train_epoch_end", on_epoch_end)
                    train_kw["device"] = "cpu"
                    results = model.train(**train_kw)
                else:
                    raise

            if results and hasattr(results, "save_dir"):
                best = Path(results.save_dir) / "weights" / "best.pt"
                if best.exists():
                    result_holder.append(best)
            if on_progress:
                on_progress(1.0, "Training finished.")
        except StopTrainingRequested:
            cancelled = True
            if on_progress:
                on_progress(-1.0, "Обучение остановлено.")
            if console_queue:
                console_queue.put("[Остановлено пользователем]")
        finally:
            if old_out is not None and old_err is not None:
                restore_stdout_stderr(old_out, old_err)
            # Восстановить COMET_* env после обучения
            if comet_prev:
                try:
                    from app.features.comet_integration.service import restore_comet_env

                    restore_comet_env(comet_prev)
                except Exception:
                    import logging

                    logging.getLogger(__name__).debug(
                        "Optional integration setup failed", exc_info=True
                    )
        if cancelled:
            return None
        if result_holder:
            return result_holder[0]
        return None

    def stop(self) -> None:
        self._stop_requested.set()
