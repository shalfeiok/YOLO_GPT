"""Constants for the training tab (SOLID: single place for magic numbers and copy)."""

CONSOLE_MAX_LINES = 2000
MAX_DATASETS = 10
METRICS_UPDATE_MS = 1000

METRICS_HEADERS_RU = (
    "Epoch",
    "GPU_mem",
    "box_loss",
    "cls_loss",
    "dfl_loss",
    "Instances",
    "Size",
)

METRICS_TOOLTIP_RU_BASE = (
    "Epoch — текущая эпоха / всего\n"
    "GPU_mem — занято памяти GPU (ГБ)\n"
    "box_loss — ошибка по bbox (чем меньше, тем лучше)\n"
    "cls_loss — ошибка по классам\n"
    "dfl_loss — распределение по границам\n"
    "Instances — число объектов в батче\n"
    "Size — размер изображения (норма)\n"
    "Тренд: потери должны снижаться по эпохам."
)
