"""
Бэкенд визуализации: GPU-ориентированный путь — ресайз на PyTorch (GPU), один
скачивание в CPU только для imshow. Опционально захват «Весь экран» через D3DShot.
При отсутствии d3dshot/torch — fallback на OpenCV.
"""
from __future__ import annotations

import logging
import time
from queue import Empty, Queue
from threading import Thread
from typing import Any, Callable, Optional, Union
try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None  # type: ignore



def _require_cv2() -> None:
    if cv2 is None:
        raise ImportError("OpenCV (cv2) is required for this feature. Install with: pip install opencv-python")
import numpy as np

log = logging.getLogger(__name__)

from app.features.detection_visualization.backends.base import IVisualizationBackend
from app.features.detection_visualization.domain import (
    BACKEND_D3DSHOT_PYTORCH,
    VISUALIZATION_BACKEND_DISPLAY_NAMES,
    default_visualization_config,
    get_config_section,
)

_d3dshot = None
_torch = None


def _lazy_d3dshot():  # type: ignore
    global _d3dshot
    if _d3dshot is None:
        try:
            import d3dshot
            _d3dshot = d3dshot
        except ImportError:
            pass
    return _d3dshot


def _lazy_torch():  # type: ignore
    global _torch
    if _torch is None:
        try:
            import torch
            _torch = torch
        except ImportError:
            pass
    return _torch


def _resize_tensor_gpu(
    img: Union[np.ndarray, Any], max_w: int, max_h: int, force_cpu: bool = False
) -> np.ndarray:
    """
    Ресайз на GPU через PyTorch (или CPU при force_cpu). Данные по возможности остаются на GPU
    до одного скачивания в numpy для imshow. Принимает numpy (загрузка на GPU) или уже
    torch.Tensor на GPU (без лишней загрузки).
    BGR HWC uint8 -> BGR HWC uint8.
    """
    torch = _lazy_torch()
    if torch is None:
        if isinstance(img, np.ndarray):
            return cv2.resize(img, (max_w, max_h), interpolation=cv2.INTER_LINEAR)
        return _numpy_fallback_resize(img, max_w, max_h)
    try:
        import torch.nn.functional as F

        use_cuda = torch.cuda.is_available() and not force_cpu
        dev = torch.device("cuda" if use_cuda else "cpu")
        if isinstance(img, np.ndarray):
            t = torch.from_numpy(img).to(dev)
        else:
            t = img if img.is_cuda else img.to(dev)
        if t.dim() == 3:
            t = t.unsqueeze(0)
        if t.shape[-1] == 3:
            t = t.permute(0, 3, 1, 2)
        if t.dtype != torch.float32:
            t = t.float() / 255.0
        t = F.interpolate(t, size=(max_h, max_w), mode="bilinear", align_corners=False)
        t = (t * 255).clamp(0, 255).byte()
        t = t[0].permute(1, 2, 0).cpu().numpy()
        return t
    except Exception:
        return _numpy_fallback_resize(img, max_w, max_h)


def _tensor_to_numpy_hwc(tensor: Any) -> np.ndarray:
    """Тензор (GPU/CPU) HWC или CHW uint8 → numpy HWC. Без ресайза, минимум копирований."""
    torch = _lazy_torch()
    if torch is None or not hasattr(tensor, "cpu"):
        return _numpy_fallback_resize(tensor, 1, 1)
    t = tensor.cpu()
    if t.dim() == 3 and t.shape[-1] == 3:
        return t.numpy()
    if t.dim() == 3 and t.shape[0] == 3:
        return t.permute(1, 2, 0).numpy()
    return t.numpy()


def _numpy_fallback_resize(img: Any, max_w: int, max_h: int) -> np.ndarray:
    """Fallback: скачать в numpy и ресайз OpenCV."""
    if isinstance(img, np.ndarray):
        h, w = img.shape[:2]
        r = min(max_w / w, max_h / h)
        nw, nh = int(w * r), int(h * r)
        return cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    try:
        arr = img.cpu().numpy() if hasattr(img, "cpu") else np.array(img)
        if len(arr.shape) == 3 and arr.shape[0] == 3:
            arr = arr.transpose(1, 2, 0)
        h, w = arr.shape[:2]
        r = min(max_w / w, max_h / h)
        nw, nh = int(w * r), int(h * r)
        return cv2.resize(arr, (nw, nh), interpolation=cv2.INTER_LINEAR)
    except Exception:
        return np.zeros((max_h, max_w, 3), dtype=np.uint8)


class D3DShotPyTorchBackend(IVisualizationBackend):
    """Отрисовка: ресайз на PyTorch GPU/CPU; опционально захват через D3DShot. Варианты по backend_id."""

    def __init__(self, backend_id: str = BACKEND_D3DSHOT_PYTORCH) -> None:
        self._backend_id = backend_id if backend_id in VISUALIZATION_BACKEND_DISPLAY_NAMES else BACKEND_D3DSHOT_PYTORCH
        section = get_config_section(self._backend_id)
        self._settings = default_visualization_config().get(section, {}).copy()
        self._display_thread: Optional[Thread] = None
        self._running = False
        self._d3d_instance = None

    def get_id(self) -> str:
        return self._backend_id

    def get_display_name(self) -> str:
        return VISUALIZATION_BACKEND_DISPLAY_NAMES.get(self._backend_id, "D3DShot + PyTorch (GPU тензоры)")

    def get_default_settings(self) -> dict[str, Any]:
        from app.features.detection_visualization.domain import (
            BACKEND_D3DSHOT_PYTORCH_CPU,
            BACKEND_D3DSHOT_FP16,
            BACKEND_D3DSHOT_TORCHSCRIPT,
        )
        return {
            "preview_max_w": 0,
            "preview_max_h": 0,
            "use_d3dshot_capture": True,
            "force_cpu": self._backend_id == BACKEND_D3DSHOT_PYTORCH_CPU,
            "use_fp16": self._backend_id == BACKEND_D3DSHOT_FP16,
            "use_torchscript": self._backend_id == BACKEND_D3DSHOT_TORCHSCRIPT,
        }

    def get_settings_schema(self) -> list[dict[str, Any]]:
        return [
            {"key": "preview_max_w", "type": "int", "label": "Ширина превью (px)", "default": 0, "min": 0, "max": 7680},
            {"key": "preview_max_h", "type": "int", "label": "Высота превью (px)", "default": 0, "min": 0, "max": 4320},
            {"key": "use_d3dshot_capture", "type": "bool", "label": "Захват «Весь экран» через D3DShot", "default": True},
            {"key": "force_cpu", "type": "bool", "label": "CPU fallback (инференс на CPU)", "default": False},
            {"key": "use_fp16", "type": "bool", "label": "Half precision (fp16, если CUDA)", "default": False},
            {"key": "use_torchscript", "type": "bool", "label": "TorchScript", "default": False},
        ]

    def get_settings(self) -> dict[str, Any]:
        return dict(self._settings)

    def apply_settings(self, settings: dict[str, Any]) -> None:
        self._settings.update(settings)

    def supports_d3dshot_capture(self) -> bool:
        return bool(_lazy_d3dshot()) and self._settings.get("use_d3dshot_capture", True)

    def capture_frame_fullscreen(self) -> Optional[np.ndarray]:
        """Захват всего экрана через D3DShot. Возвращает BGR numpy или None."""
        d3d = _lazy_d3dshot()
        if not d3d or not self._settings.get("use_d3dshot_capture", True):
            return None
        try:
            if self._d3d_instance is None:
                self._d3d_instance = d3d.create()
            shot = self._d3d_instance.screenshot()
            if shot is None:
                return None
            if hasattr(shot, "numpy"):
                arr = shot.numpy()
            else:
                arr = np.array(shot)
            if arr is None or arr.size == 0:
                return None
            if len(arr.shape) == 3 and arr.shape[2] == 4:
                arr = arr[:, :, :3]
            if len(arr.shape) == 3 and arr.shape[2] == 3:
                arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            return arr
        except Exception:
            return None

    def start_display(
        self,
        run_id: int,
        window_name: str,
        preview_queue: Queue,
        max_w: int,
        max_h: int,
        is_running_getter: Callable[[], bool],
        run_id_getter: Callable[[], int],
        on_stop: Optional[Callable[[], None]] = None,
        on_q_key: Optional[Callable[[], None]] = None,
        on_render_metrics: Optional[Callable[[float], None]] = None,
    ) -> None:
        max_w = self._settings.get("preview_max_w", max_w)
        max_h = self._settings.get("preview_max_h", max_h)
        no_resize = max_w <= 0 or max_h <= 0

        # OpenCV на Windows нестабильно создаёт окна с пробелами в имени — используем только ASCII и run_id
        cv2_window_name = "YOLO_%d" % run_id

        def display_loop() -> None:
            self._running = True
            try:
                try:
                    cv2.destroyWindow(cv2_window_name)
                except Exception:
                    import logging
                    logging.getLogger(__name__).debug('OpenCV window operation failed', exc_info=True)
                cv2.namedWindow(cv2_window_name, cv2.WINDOW_NORMAL)
                if not no_resize:
                    cv2.resizeWindow(cv2_window_name, max_w, max_h)
            except cv2.error as e:
                if on_stop:
                    on_stop()
                return
            img = None
            try:
                while self._running and is_running_getter() and run_id_getter() == run_id:
                    try:
                        img = preview_queue.get(timeout=0.05)
                    except Empty:
                        pass
                    # PreviewBuffer.get_nowait() does not remove frame — do not drain in a loop or we never reach imshow
                    try:
                        img = preview_queue.get_nowait()
                    except Empty:
                        pass
                    is_numpy = (
                        img is not None
                        and isinstance(img, np.ndarray)
                        and img.dtype == np.uint8
                        and len(img.shape) == 3
                    )
                    is_tensor = (
                        img is not None
                        and hasattr(img, "is_cuda")
                        and hasattr(img, "shape")
                        and len(img.shape) == 3
                    )
                    if is_numpy or is_tensor:
                        try:
                            t0 = time.perf_counter()
                            if no_resize:
                                out = img if is_numpy else _tensor_to_numpy_hwc(img)
                            else:
                                if is_numpy:
                                    h, w = img.shape[:2]
                                else:
                                    if img.shape[2] == 3:
                                        h, w = img.shape[0], img.shape[1]
                                    else:
                                        h, w = img.shape[1], img.shape[2]
                                if w <= max_w and h <= max_h:
                                    out = img if is_numpy else _tensor_to_numpy_hwc(img)
                                else:
                                    r = min(max_w / w, max_h / h)
                                    nw, nh = int(w * r), int(h * r)
                                    force_cpu = self._settings.get("force_cpu", False)
                                    out = _resize_tensor_gpu(img, nw, nh, force_cpu=force_cpu)
                            if out is not None:
                                out = np.ascontiguousarray(out) if isinstance(out, np.ndarray) else out
                                cv2.imshow(cv2_window_name, out)
                            if on_render_metrics:
                                on_render_metrics((time.perf_counter() - t0) * 1000.0)
                        except Exception:
                            log.exception("Ошибка в display_loop (D3DShot/PyTorch resize/imshow)")
                    if cv2.waitKey(1) & 0xFF == ord("q") and on_q_key:
                        on_q_key()
                        break
            finally:
                try:
                    cv2.destroyWindow(cv2_window_name)
                except Exception:
                    try:
                        cv2.destroyAllWindows()
                    except Exception:
                        import logging
                        logging.getLogger(__name__).debug('OpenCV window operation failed', exc_info=True)
                self._running = False
                if on_stop:
                    on_stop()

        self._display_thread = Thread(target=display_loop, daemon=True)
        self._display_thread.start()

    def stop_display(self) -> None:
        self._running = False
        self._d3d_instance = None
        t = self._display_thread
        self._display_thread = None
        if t is not None and t.is_alive():
            t.join(timeout=2.0)
