"""
Business logic: build Albumentations transform list for Ultralytics model.train(augmentations=...).

Ref: https://docs.ultralytics.com/ru/integrations/albumentations/#custom-albumentations-transforms

Важно: Ultralytics при отсутствии параметра augmentations подставляет свои трансформы по умолчанию
(Blur, MedianBlur, ToGray, CLAHE с p=0.01). Поэтому мы всегда возвращаем список: пустой при отключении,
иначе — трансформы согласно настройкам из вкладки «Обучение» (вероятность p из формы).
"""

from __future__ import annotations

from typing import Any

from app.features.albumentations_integration.domain import AlbumentationsConfig


def get_albumentations_transforms(config: AlbumentationsConfig) -> list[Any]:
    """
    Возвращает список трансформов Albumentations для model.train(augmentations=...).
    - Если аугментация отключена: пустой список [] — Ultralytics не применит albumentations.
    - Если включена «Стандартные» без кастомных: список по умолчанию (Blur, MedianBlur, ToGray, CLAHE) с config.transform_p.
    - Если включены кастомные: список из custom_transforms с их p.
    """
    if not config.enabled:
        return []
    try:
        import albumentations as A
    except ImportError:
        return []
    p = config.transform_p
    out: list[Any] = []
    if config.use_standard and not config.custom_transforms:
        # Стандартный набор как в Ultralytics, но с вероятностью p из настроек
        out = [
            A.Blur(blur_limit=(3, 7), p=p),
            A.MedianBlur(blur_limit=(3, 7), p=p),
            A.ToGray(num_output_channels=3, p=p),
            A.CLAHE(clip_limit=(1.0, 4.0), tile_grid_size=(8, 8), p=p),
        ]
    else:
        for t in config.custom_transforms:
            name = t.get("name") or t.get("transform")
            tp = float(t.get("p", p))
            if name == "Blur":
                out.append(A.Blur(blur_limit=t.get("blur_limit", 7), p=tp))
            elif name == "MedianBlur":
                out.append(A.MedianBlur(blur_limit=t.get("blur_limit", 7), p=tp))
            elif name == "ToGray":
                out.append(A.ToGray(num_output_channels=3, p=tp))
            elif name == "CLAHE":
                out.append(A.CLAHE(clip_limit=float(t.get("clip_limit", 4.0)), p=tp))
            elif name == "GaussNoise":
                out.append(A.GaussNoise(var_limit=(10.0, 50.0), p=tp))
            elif name == "RandomBrightnessContrast":
                out.append(
                    A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=tp)
                )
            elif name == "HueSaturationValue":
                out.append(
                    A.HueSaturationValue(
                        hue_shift_limit=20, sat_shift_limit=30, val_shift_limit=20, p=tp
                    )
                )
    return out
