"""
Домен настроек визуализации детекции: выбор бэкенда отрисовки (OpenCV, D3DShot+PyTorch, ONNX) и настройки по умолчанию.
Инференс определяется бэкендом: ONNX — detector_onnx, остальные — Ultralytics (PyTorch).
"""

from __future__ import annotations

from typing import Any

# Legacy (обратная совместимость)
BACKEND_OPENCV = "opencv"
BACKEND_D3DSHOT_PYTORCH = "d3dshot_pytorch"
BACKEND_ONNX = "onnx"

# ONNX варианты (execution provider)
BACKEND_ONNX_CPU = "onnx_cpu"
BACKEND_ONNX_CUDA = "onnx_cuda"
BACKEND_ONNX_DIRECTML = "onnx_directml"
BACKEND_ONNX_TENSORRT = "onnx_tensorrt"
BACKEND_ONNX_AUTO = "onnx_auto"

# D3DShot + PyTorch варианты
BACKEND_D3DSHOT_PYTORCH_GPU = "d3dshot_pytorch_gpu"
BACKEND_D3DSHOT_PYTORCH_CPU = "d3dshot_pytorch_cpu"
BACKEND_D3DSHOT_TORCHSCRIPT = "d3dshot_torchscript"
BACKEND_D3DSHOT_FP16 = "d3dshot_fp16"

# OpenCV варианты (захват / ресайз)
BACKEND_OPENCV_GDI = "opencv_gdi"
BACKEND_OPENCV_MSS = "opencv_mss"
BACKEND_OPENCV_IMSHOW = "opencv_imshow"
BACKEND_OPENCV_CUDA_RESIZE = "opencv_cuda_resize"
BACKEND_OPENCV_CPU_RESIZE = "opencv_cpu_resize"

# Все ID (legacy + новые). list_backends() фильтрует по доступности.
VISUALIZATION_BACKEND_IDS = [
    BACKEND_OPENCV,
    BACKEND_OPENCV_GDI,
    BACKEND_OPENCV_MSS,
    BACKEND_OPENCV_IMSHOW,
    BACKEND_OPENCV_CUDA_RESIZE,
    BACKEND_OPENCV_CPU_RESIZE,
    BACKEND_D3DSHOT_PYTORCH,
    BACKEND_D3DSHOT_PYTORCH_GPU,
    BACKEND_D3DSHOT_PYTORCH_CPU,
    BACKEND_D3DSHOT_TORCHSCRIPT,
    BACKEND_D3DSHOT_FP16,
    BACKEND_ONNX,
    BACKEND_ONNX_CPU,
    BACKEND_ONNX_CUDA,
    BACKEND_ONNX_DIRECTML,
    BACKEND_ONNX_TENSORRT,
    BACKEND_ONNX_AUTO,
]

VISUALIZATION_BACKEND_DISPLAY_NAMES: dict[str, str] = {
    BACKEND_OPENCV: "OpenCV (GDI/mss + imshow)",
    BACKEND_OPENCV_GDI: "OpenCV + GDI (Windows)",
    BACKEND_OPENCV_MSS: "OpenCV + MSS",
    BACKEND_OPENCV_IMSHOW: "OpenCV + cv2.imshow",
    BACKEND_OPENCV_CUDA_RESIZE: "OpenCV + CUDA resize",
    BACKEND_OPENCV_CPU_RESIZE: "OpenCV + CPU resize",
    BACKEND_D3DSHOT_PYTORCH: "D3DShot + PyTorch (GPU тензоры)",
    BACKEND_D3DSHOT_PYTORCH_GPU: "D3DShot + PyTorch (GPU tensor inference)",
    BACKEND_D3DSHOT_PYTORCH_CPU: "D3DShot + PyTorch (CPU fallback)",
    BACKEND_D3DSHOT_TORCHSCRIPT: "D3DShot + TorchScript",
    BACKEND_D3DSHOT_FP16: "D3DShot + half precision (fp16)",
    BACKEND_ONNX: "ONNX (автовыбор провайдера)",
    BACKEND_ONNX_CPU: "ONNX (CPU)",
    BACKEND_ONNX_CUDA: "ONNX (CUDA GPU)",
    BACKEND_ONNX_DIRECTML: "ONNX (DirectML)",
    BACKEND_ONNX_TENSORRT: "ONNX (TensorRT)",
    BACKEND_ONNX_AUTO: "ONNX (автовыбор провайдера)",
}

# Секция конфига по backend_id (для загрузки/сохранения настроек)
BACKEND_CONFIG_SECTION: dict[str, str] = {
    BACKEND_OPENCV: "opencv",
    BACKEND_OPENCV_GDI: "opencv",
    BACKEND_OPENCV_MSS: "opencv",
    BACKEND_OPENCV_IMSHOW: "opencv",
    BACKEND_OPENCV_CUDA_RESIZE: "opencv",
    BACKEND_OPENCV_CPU_RESIZE: "opencv",
    BACKEND_D3DSHOT_PYTORCH: "d3dshot_pytorch",
    BACKEND_D3DSHOT_PYTORCH_GPU: "d3dshot_pytorch",
    BACKEND_D3DSHOT_PYTORCH_CPU: "d3dshot_pytorch",
    BACKEND_D3DSHOT_TORCHSCRIPT: "d3dshot_pytorch",
    BACKEND_D3DSHOT_FP16: "d3dshot_pytorch",
    BACKEND_ONNX: "onnx",
    BACKEND_ONNX_CPU: "onnx",
    BACKEND_ONNX_CUDA: "onnx",
    BACKEND_ONNX_DIRECTML: "onnx",
    BACKEND_ONNX_TENSORRT: "onnx",
    BACKEND_ONNX_AUTO: "onnx",
}


def get_config_section(backend_id: str) -> str:
    """Секция в конфиге для backend_id (opencv / d3dshot_pytorch / onnx)."""
    return BACKEND_CONFIG_SECTION.get(backend_id, "opencv")


def is_onnx_family(backend_id: str) -> bool:
    """Использовать detector_onnx для инференса."""
    section = get_config_section(backend_id)
    return section == "onnx"


def use_gpu_tensor_for_preview(backend_id: str) -> bool:
    """Передавать кадры в превью как GPU-тензоры (D3DShot GPU / fp16)."""
    return backend_id in (
        BACKEND_D3DSHOT_PYTORCH,
        BACKEND_D3DSHOT_PYTORCH_GPU,
        BACKEND_D3DSHOT_FP16,
    )


def default_visualization_config() -> dict[str, Any]:
    """Конфиг по умолчанию: D3DShot+PyTorch, качество как в источнике (0 = без ресайза)."""
    return {
        "backend_id": BACKEND_D3DSHOT_PYTORCH,
        "opencv": {
            "preview_max_w": 0,
            "preview_max_h": 0,
            "use_cuda_resize": True,
            "capture_method": "gdi",  # gdi | mss | imshow
        },
        "d3dshot_pytorch": {
            "preview_max_w": 0,
            "preview_max_h": 0,
            "use_d3dshot_capture": True,
            "force_cpu": False,
            "use_fp16": False,
            "use_torchscript": False,
        },
        "onnx": {
            "preview_max_w": 0,
            "preview_max_h": 0,
            "use_cuda_resize": True,
            "execution_provider": "auto",  # cpu | cuda | directml | tensorrt | auto
            "use_directml": False,
            "use_tensorrt": False,
        },
        "presets": [],
    }


def builtin_visualization_presets() -> list[tuple[str, dict[str, Any]]]:
    """Встроенные пресеты: (название, полный конфиг). 0×0 = без ресайза."""

    def make_config(backend: str, max_w: int, max_h: int) -> dict[str, Any]:
        d = default_visualization_config()
        return {
            "backend_id": backend,
            "opencv": {
                "preview_max_w": max_w,
                "preview_max_h": max_h,
                "use_cuda_resize": d["opencv"]["use_cuda_resize"],
                "capture_method": d["opencv"].get("capture_method", "gdi"),
            },
            "d3dshot_pytorch": {
                "preview_max_w": max_w,
                "preview_max_h": max_h,
                "use_d3dshot_capture": d["d3dshot_pytorch"]["use_d3dshot_capture"],
                "force_cpu": d["d3dshot_pytorch"].get("force_cpu", False),
                "use_fp16": d["d3dshot_pytorch"].get("use_fp16", False),
                "use_torchscript": d["d3dshot_pytorch"].get("use_torchscript", False),
            },
            "onnx": {
                "preview_max_w": max_w,
                "preview_max_h": max_h,
                "use_cuda_resize": d["onnx"]["use_cuda_resize"],
                "execution_provider": d["onnx"].get("execution_provider", "auto"),
                "use_directml": d["onnx"].get("use_directml", False),
                "use_tensorrt": d["onnx"].get("use_tensorrt", False),
            },
            "presets": d.get("presets", []),
        }

    return [
        ("Исходное качество (без ресайза)", make_config(BACKEND_D3DSHOT_PYTORCH, 0, 0)),
        ("854×480", make_config(BACKEND_D3DSHOT_PYTORCH, 854, 480)),
        ("1280×720", make_config(BACKEND_D3DSHOT_PYTORCH, 1280, 720)),
        ("1920×1080", make_config(BACKEND_D3DSHOT_PYTORCH, 1920, 1080)),
        ("OpenCV 854×480", make_config(BACKEND_OPENCV, 854, 480)),
        ("OpenCV исходное качество", make_config(BACKEND_OPENCV, 0, 0)),
        ("ONNX 854×480", make_config(BACKEND_ONNX, 854, 480)),
        ("ONNX исходное качество", make_config(BACKEND_ONNX, 0, 0)),
    ]
