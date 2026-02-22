"""Конфигурация приложения и константы.

Содержит пути к корню проекта, датасетам, runs, параметры детекции и обучения,
путь к файлу конфигурации интеграций (integrations_config.json).
"""

from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET1 = PROJECT_ROOT / "dataset" / "dataset1"
DEFAULT_DATASET2 = PROJECT_ROOT / "dataset" / "dataset2"
DEFAULT_RUNS_DIR = PROJECT_ROOT / "runs" / "detect"
DEFAULT_WEIGHTS_DIR = PROJECT_ROOT / "weights"

# Detection
DEFAULT_CONFIDENCE = 0.45
DEFAULT_IOU_THRESH = 0.45
PREVIEW_MAX_SIZE = (
    854,
    480,
)  # smaller to reduce Tk/PhotoImage load and avoid main-thread freeze during long detection

# Training defaults (подобраны под типичную связку: 6-ядерный CPU + 8 GB GPU, напр. Ryzen 5 2600 + RTX 5060)
DEFAULT_EPOCHS = 50
DEFAULT_BATCH = -1  # -1 = авто по документации Ultralytics (для 8 GB обычно 16–32)
DEFAULT_IMGSZ = 640
DEFAULT_PATIENCE = 20
DEFAULT_WORKERS = 6  # ≈ число ядер CPU; больше — рост нагрузки на CPU/RAM и просадка GPU
DEFAULT_DEVICE = ""  # auto

# Integrations tab config (JSON)
INTEGRATIONS_CONFIG_PATH = PROJECT_ROOT / "integrations_config.json"
# Визуализация детекции: бэкенд отрисовки и настройки (JSON)
DETECTION_VISUALIZATION_CONFIG_PATH = PROJECT_ROOT / "detection_visualization_config.json"
