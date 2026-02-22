"""
Загрузка/сохранение конфигурации визуализации детекции (JSON).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.features.detection_visualization.domain import (
    default_visualization_config,
)


def load_visualization_config(path: Path | None = None) -> dict[str, Any]:
    """Загрузить конфиг визуализации. При отсутствии файла — дефолт."""
    from app.config import DETECTION_VISUALIZATION_CONFIG_PATH

    p = path or DETECTION_VISUALIZATION_CONFIG_PATH
    if not p.exists():
        return default_visualization_config()
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return default_visualization_config()

    if not isinstance(data, dict):
        return default_visualization_config()
    defaults = default_visualization_config()
    for key in defaults:
        if key not in data:
            data[key] = defaults[key]
        elif isinstance(defaults.get(key), dict) and isinstance(data.get(key), dict):
            for k, v in defaults[key].items():
                if k not in data[key]:
                    data[key][k] = v
    return data


def save_visualization_config(config: dict[str, Any], path: Path | None = None) -> None:
    """Сохранить конфиг визуализации."""
    from app.config import DETECTION_VISUALIZATION_CONFIG_PATH

    p = path or DETECTION_VISUALIZATION_CONFIG_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_user_presets() -> list[dict[str, Any]]:
    """Список сохранённых пресетов: [{"name": str, "config": dict}, ...]."""
    data = load_visualization_config()
    return list(data.get("presets", []))


def save_user_preset(name: str, config: dict[str, Any], path: Path | None = None) -> None:
    """Добавить или обновить пресет по имени. config — полный конфиг визуализации (без presets)."""
    data = load_visualization_config(path)
    presets = list(data.get("presets", []))
    # Убрать старый с таким именем
    presets = [p for p in presets if p.get("name") != name]
    presets.append({"name": name, "config": {k: v for k, v in config.items() if k != "presets"}})
    data["presets"] = presets
    save_visualization_config(data, path)


def delete_user_preset(name: str, path: Path | None = None) -> None:
    """Удалить сохранённый пресет по имени."""
    data = load_visualization_config(path)
    presets = [p for p in data.get("presets", []) if p.get("name") != name]
    data["presets"] = presets
    save_visualization_config(data, path)
