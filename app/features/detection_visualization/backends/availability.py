"""
Проверка доступности провайдеров и возможностей для graceful fallback в списке бэкендов.
"""

from __future__ import annotations

import sys


def cuda_available() -> bool:
    """CUDA доступна (PyTorch или через onnxruntime)."""
    try:
        import torch

        return bool(torch.cuda.is_available())
    except ImportError:
        pass
    try:
        import onnxruntime as ort

        return "CUDAExecutionProvider" in ort.get_available_providers()
    except ImportError:
        pass
    return False


def directml_available() -> bool:
    """DirectML доступен (Windows, onnxruntime-directml)."""
    if sys.platform != "win32":
        return False
    try:
        import onnxruntime as ort

        return "DmlExecutionProvider" in ort.get_available_providers()
    except ImportError:
        return False


def tensorrt_available() -> bool:
    """TensorRT execution provider доступен."""
    try:
        import onnxruntime as ort

        return "TensorrtExecutionProvider" in ort.get_available_providers()
    except ImportError:
        return False


def onnx_available_providers() -> tuple[bool, bool, bool, bool]:
    """(cpu, cuda, directml, tensorrt) доступность для ONNX."""
    try:
        import onnxruntime as ort

        prov = set(ort.get_available_providers())
        return (
            "CPUExecutionProvider" in prov,
            "CUDAExecutionProvider" in prov,
            "DmlExecutionProvider" in prov,
            "TensorrtExecutionProvider" in prov,
        )
    except ImportError:
        return (True, False, False, False)


def opencv_cuda_resize_available() -> bool:
    """OpenCV собран с cv2.cuda (ресайз на GPU)."""
    try:
        import cv2

        cuda = getattr(cv2, "cuda", None)
        return cuda is not None and cuda.getCudaEnabledDeviceCount() > 0
    except Exception:
        return False


def d3dshot_available() -> bool:
    """D3DShot доступен (захват экрана Windows)."""
    if sys.platform != "win32":
        return False
    try:
        import d3dshot

        return d3dshot is not None
    except ImportError:
        return False
