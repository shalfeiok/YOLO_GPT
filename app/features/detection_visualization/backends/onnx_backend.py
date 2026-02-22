"""
Бэкенд визуализации ONNX: тот же путь отрисовки, что и OpenCV (resize + imshow).
Захват — GDI/mss/камера. Инференс — ONNX (выбор детектора в view по backend_id).
Варианты по execution provider: CPU, CUDA, DirectML, TensorRT, auto.
"""

from __future__ import annotations

from typing import Any

from app.features.detection_visualization.backends.opencv_backend import OpenCVBackend
from app.features.detection_visualization.domain import (
    BACKEND_ONNX,
    BACKEND_ONNX_AUTO,
    BACKEND_ONNX_CPU,
    BACKEND_ONNX_CUDA,
    BACKEND_ONNX_DIRECTML,
    BACKEND_ONNX_TENSORRT,
    VISUALIZATION_BACKEND_DISPLAY_NAMES,
    default_visualization_config,
    get_config_section,
)

_ONNX_PROVIDER_BY_BACKEND = {
    BACKEND_ONNX_CPU: "cpu",
    BACKEND_ONNX_CUDA: "cuda",
    BACKEND_ONNX_DIRECTML: "directml",
    BACKEND_ONNX_TENSORRT: "tensorrt",
    BACKEND_ONNX_AUTO: "auto",
    BACKEND_ONNX: "auto",
}


class OnnxBackend(OpenCVBackend):
    """Отрисовка для режима ONNX: те же настройки и display-поток, что у OpenCV. Варианты по backend_id."""

    def __init__(self, backend_id: str = BACKEND_ONNX) -> None:
        super().__init__(backend_id)
        section = get_config_section(backend_id)
        self._settings = default_visualization_config().get(section, {}).copy()
        self._backend_id = (
            backend_id if backend_id in VISUALIZATION_BACKEND_DISPLAY_NAMES else BACKEND_ONNX
        )

    def get_id(self) -> str:
        return self._backend_id

    def get_display_name(self) -> str:
        return VISUALIZATION_BACKEND_DISPLAY_NAMES.get(self._backend_id, "ONNX (автовыбор)")

    def get_default_settings(self) -> dict[str, Any]:
        base = super().get_default_settings()
        provider = _ONNX_PROVIDER_BY_BACKEND.get(self._backend_id, "auto")
        base["execution_provider"] = provider
        base["use_directml"] = self._backend_id == BACKEND_ONNX_DIRECTML
        base["use_tensorrt"] = self._backend_id == BACKEND_ONNX_TENSORRT
        return base

    def get_settings_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "key": "preview_max_w",
                "type": "int",
                "label": "Ширина превью (px)",
                "default": 0,
                "min": 0,
                "max": 7680,
            },
            {
                "key": "preview_max_h",
                "type": "int",
                "label": "Высота превью (px)",
                "default": 0,
                "min": 0,
                "max": 4320,
            },
            {
                "key": "use_cuda_resize",
                "type": "bool",
                "label": "Ресайз на GPU (cv2.cuda)",
                "default": True,
            },
            {
                "key": "execution_provider",
                "type": "choice",
                "label": "Execution provider",
                "default": "auto",
                "choices": ["cpu", "cuda", "directml", "tensorrt", "auto"],
            },
            {
                "key": "use_directml",
                "type": "bool",
                "label": "DirectML (если доступен)",
                "default": False,
            },
            {
                "key": "use_tensorrt",
                "type": "bool",
                "label": "TensorRT (если доступен)",
                "default": False,
            },
        ]
