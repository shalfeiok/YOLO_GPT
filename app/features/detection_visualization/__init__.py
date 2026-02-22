"""
Визуализация детекции: выбор бэкенда отрисовки (OpenCV, D3DShot+PyTorch, ONNX),
настройки и их сохранение.
"""

from __future__ import annotations

from app.features.detection_visualization.backends import get_backend, list_backends
from app.features.detection_visualization.domain import (
    BACKEND_D3DSHOT_PYTORCH,
    BACKEND_ONNX,
    BACKEND_OPENCV,
    VISUALIZATION_BACKEND_DISPLAY_NAMES,
    default_visualization_config,
    get_config_section,
    is_onnx_family,
    use_gpu_tensor_for_preview,
)
from app.features.detection_visualization.repository import (
    load_visualization_config,
    save_visualization_config,
)


def reset_visualization_config_to_default() -> None:
    """Reset visualization config to defaults and persist it."""
    save_visualization_config(default_visualization_config())


"""Detection visualization integration (headless-safe).

UI helpers are intentionally not imported here because they may depend on
optional GUI toolkits.
"""

__all__ = [
    "get_backend",
    "list_backends",
    "BACKEND_OPENCV",
    "BACKEND_D3DSHOT_PYTORCH",
    "BACKEND_ONNX",
    "VISUALIZATION_BACKEND_DISPLAY_NAMES",
    "default_visualization_config",
    "get_config_section",
    "is_onnx_family",
    "use_gpu_tensor_for_preview",
    "load_visualization_config",
    "save_visualization_config",
    "reset_visualization_config_to_default",
]
