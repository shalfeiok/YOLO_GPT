"""
Бэкенды визуализации детекции: OpenCV, D3DShot + PyTorch, ONNX (все варианты).
list_backends() возвращает только доступные варианты (graceful fallback).
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Type

from app.features.detection_visualization.backends.availability import (
    cuda_available,
    directml_available,
    opencv_cuda_resize_available,
    tensorrt_available,
)
from app.features.detection_visualization.backends.base import IVisualizationBackend
from app.features.detection_visualization.backends.d3dshot_pytorch_backend import (
    D3DShotPyTorchBackend,
)
from app.features.detection_visualization.backends.onnx_backend import OnnxBackend
from app.features.detection_visualization.backends.opencv_backend import OpenCVBackend
from app.features.detection_visualization.domain import (
    BACKEND_D3DSHOT_FP16,
    BACKEND_D3DSHOT_PYTORCH,
    BACKEND_D3DSHOT_PYTORCH_CPU,
    BACKEND_D3DSHOT_PYTORCH_GPU,
    BACKEND_D3DSHOT_TORCHSCRIPT,
    BACKEND_ONNX,
    BACKEND_ONNX_AUTO,
    BACKEND_ONNX_CPU,
    BACKEND_ONNX_CUDA,
    BACKEND_ONNX_DIRECTML,
    BACKEND_ONNX_TENSORRT,
    BACKEND_OPENCV,
    BACKEND_OPENCV_CPU_RESIZE,
    BACKEND_OPENCV_CUDA_RESIZE,
    BACKEND_OPENCV_GDI,
    BACKEND_OPENCV_IMSHOW,
    BACKEND_OPENCV_MSS,
    VISUALIZATION_BACKEND_DISPLAY_NAMES,
)


def _backend_factory(
    backend_id: str,
) -> tuple[type[IVisualizationBackend], str]:
    """(BackendClass, backend_id) для создания инстанса."""
    opencv_ids = {
        BACKEND_OPENCV,
        BACKEND_OPENCV_GDI,
        BACKEND_OPENCV_MSS,
        BACKEND_OPENCV_IMSHOW,
        BACKEND_OPENCV_CUDA_RESIZE,
        BACKEND_OPENCV_CPU_RESIZE,
    }
    d3d_ids = {
        BACKEND_D3DSHOT_PYTORCH,
        BACKEND_D3DSHOT_PYTORCH_GPU,
        BACKEND_D3DSHOT_PYTORCH_CPU,
        BACKEND_D3DSHOT_TORCHSCRIPT,
        BACKEND_D3DSHOT_FP16,
    }
    onnx_ids = {
        BACKEND_ONNX,
        BACKEND_ONNX_CPU,
        BACKEND_ONNX_CUDA,
        BACKEND_ONNX_DIRECTML,
        BACKEND_ONNX_TENSORRT,
        BACKEND_ONNX_AUTO,
    }
    if backend_id in opencv_ids:
        return (OpenCVBackend, backend_id)
    if backend_id in d3d_ids:
        return (D3DShotPyTorchBackend, backend_id)
    if backend_id in onnx_ids:
        return (OnnxBackend, backend_id)
    return (OpenCVBackend, BACKEND_OPENCV)


def _is_backend_available(backend_id: str) -> bool:
    """Скрывать варианты, для которых нет провайдера/возможности."""
    if backend_id == BACKEND_OPENCV_CUDA_RESIZE and not opencv_cuda_resize_available():
        return False
    if backend_id == BACKEND_ONNX_CUDA and not cuda_available():
        return False
    if backend_id == BACKEND_ONNX_DIRECTML and not directml_available():
        return False
    if backend_id == BACKEND_ONNX_TENSORRT and not tensorrt_available():
        return False
    if backend_id in (BACKEND_D3DSHOT_PYTORCH_GPU, BACKEND_D3DSHOT_FP16) and not cuda_available():
        return False
    return True


def get_backend(backend_id: str) -> IVisualizationBackend:
    """Создать инстанс бэкенда по id. Неизвестный/legacy id — маппинг на поддерживаемый."""
    cls, bid = _backend_factory(backend_id)
    return cls(bid)


def list_backends() -> list[tuple[str, str]]:
    """Список (id, display_name) для выбора в UI. Только доступные варианты (graceful fallback)."""
    from app.features.detection_visualization.domain import VISUALIZATION_BACKEND_IDS

    result: list[tuple[str, str]] = []
    seen_names: set[str] = set()
    for bid in VISUALIZATION_BACKEND_IDS:
        if not _is_backend_available(bid):
            continue
        name = VISUALIZATION_BACKEND_DISPLAY_NAMES.get(bid, bid)
        if name in seen_names:
            continue
        seen_names.add(name)
        result.append((bid, name))
    return result
