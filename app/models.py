#commit и версия
"""Модели YOLO и справочные данные для обучения.

Содержит перечисление идентификаторов моделей (YOLOModelId), список выбора для UI
(ModelChoice, YOLO_MODEL_CHOICES), подсказки (MODEL_HINTS) и рекомендуемые диапазоны эпох.
"""

from enum import Enum
from typing import NamedTuple


class YOLOModelId(str, Enum):
    """Идентификаторы моделей YOLO для обучения и инференса (имя файла .pt)."""

    YOLO26N = "yolo26n.pt"
    YOLO26S = "yolo26s.pt"
    YOLO26M = "yolo26m.pt"
    YOLO26L = "yolo26l.pt"
    YOLO26X = "yolo26x.pt"
    YOLO11N = "yolo11n.pt"
    YOLO11S = "yolo11s.pt"
    YOLO11M = "yolo11m.pt"
    YOLO11L = "yolo11l.pt"
    YOLO11X = "yolo11x.pt"
    YOLO10N = "yolo10n.pt"
    YOLO10S = "yolo10s.pt"
    YOLO10M = "yolo10m.pt"
    YOLO10L = "yolo10l.pt"
    YOLO10X = "yolo10x.pt"
    YOLO8N = "yolov8n.pt"
    YOLO8S = "yolov8s.pt"
    YOLO8M = "yolov8m.pt"
    YOLO8L = "yolov8l.pt"
    YOLO8X = "yolov8x.pt"
    YOLO5N = "yolov5n.pt"
    YOLO5S = "yolov5s.pt"
    YOLO5M = "yolov5m.pt"
    YOLO5L = "yolov5l.pt"
    YOLO5X = "yolov5x.pt"
    YOLO9C = "yolov9c.pt"
    YOLO9E = "yolov9e.pt"


class ModelChoice(NamedTuple):
    """Элемент выбора модели в UI: отображаемое имя и идентификатор (.pt)."""

    label: str
    model_id: str


# Все известные модели детекции YOLO в ultralytics (загрузка по model_id как у имеющихся)
YOLO_MODEL_CHOICES: list[ModelChoice] = [
    # YOLO26 (новейшая, NMS-free, для edge)
    ModelChoice("YOLO26 Nano", "yolo26n.pt"),
    ModelChoice("YOLO26 Small", "yolo26s.pt"),
    ModelChoice("YOLO26 Medium", "yolo26m.pt"),
    ModelChoice("YOLO26 Large", "yolo26l.pt"),
    ModelChoice("YOLO26 XLarge", "yolo26x.pt"),
    # YOLO11
    ModelChoice("YOLO11 Nano", "yolo11n.pt"),
    ModelChoice("YOLO11 Small", "yolo11s.pt"),
    ModelChoice("YOLO11 Medium", "yolo11m.pt"),
    ModelChoice("YOLO11 Large", "yolo11l.pt"),
    ModelChoice("YOLO11 XLarge", "yolo11x.pt"),
    # YOLO10
    ModelChoice("YOLO10 Nano", "yolo10n.pt"),
    ModelChoice("YOLO10 Small", "yolo10s.pt"),
    ModelChoice("YOLO10 Medium", "yolo10m.pt"),
    ModelChoice("YOLO10 Large", "yolo10l.pt"),
    ModelChoice("YOLO10 XLarge", "yolo10x.pt"),
    # YOLOv8
    ModelChoice("YOLOv8 Nano", "yolov8n.pt"),
    ModelChoice("YOLOv8 Small", "yolov8s.pt"),
    ModelChoice("YOLOv8 Medium", "yolov8m.pt"),
    ModelChoice("YOLOv8 Large", "yolov8l.pt"),
    ModelChoice("YOLOv8 XLarge", "yolov8x.pt"),
    # YOLOv9
    ModelChoice("YOLOv9-C", "yolov9c.pt"),
    ModelChoice("YOLOv9-E", "yolov9e.pt"),
    # YOLOv5
    ModelChoice("YOLOv5 Nano", "yolov5n.pt"),
    ModelChoice("YOLOv5 Small", "yolov5s.pt"),
    ModelChoice("YOLOv5 Medium", "yolov5m.pt"),
    ModelChoice("YOLOv5 Large", "yolov5l.pt"),
    ModelChoice("YOLOv5 XLarge", "yolov5x.pt"),
]

# Подсказки по моделям: рекомендации по классам, эпохам и заметки (для UI)
MODEL_HINTS: dict[str, str] = {}
for _m in YOLO_MODEL_CHOICES:
    mid = _m.model_id
    if "yolo26" in mid:
        MODEL_HINTS[mid] = (
            "Новейшая модель, NMS-free. Рекомендуется 100–300 эпох. Подходит для 1–1000+ классов."
        )
    elif "yolo11" in mid:
        MODEL_HINTS[mid] = (
            "Актуальная модель. Рекомендуется 100–300 эпох. Универсально для любого числа классов."
        )
    elif "yolo10" in mid:
        MODEL_HINTS[mid] = (
            "NMS-free. Рекомендуется 100–250 эпох. Хороший баланс скорости и точности."
        )
    elif "yolov8" in mid:
        MODEL_HINTS[mid] = (
            "Проверенная версия. Рекомендуется 100–400 эпох. Стабильный выбор для продакшена."
        )
    elif "yolov9" in mid:
        MODEL_HINTS[mid] = (
            "C/E — средний и большой размер. Рекомендуется 150–300 эпох. Точность выше при большем объёме данных."
        )
    elif "yolov5" in mid:
        MODEL_HINTS[mid] = (
            "Классика. Рекомендуется 100–500 эпох. Много классов (10–1000+) — увеличьте эпохи."
        )
    else:
        MODEL_HINTS[mid] = "Рекомендуется 100–300 эпох. Число классов без жёстких ограничений."

# Рекомендуемое число эпох по размеру модели (n/s/m/l/x)
RECOMMENDED_EPOCHS: dict[str, tuple[int, int]] = {
    "n": (100, 300),
    "s": (120, 350),
    "m": (150, 400),
    "l": (180, 500),
    "x": (200, 600),
    "c": (150, 350),
    "e": (180, 400),
}
