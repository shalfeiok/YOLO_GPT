"""
Бэкенд визуализации: классический путь OpenCV — ресайз на CPU или cv2.cuda (если
собран с CUDA), затем imshow. Захват — GDI/mss/камера вне этого модуля.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from queue import Empty, Queue
from threading import Thread
from typing import Any

try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None  # type: ignore


def _require_cv2() -> None:
    if cv2 is None:
        raise ImportError(
            "OpenCV (cv2) is required for this feature. Install with: pip install opencv-python"
        )


import numpy as np

from app.features.detection_visualization.backends.base import IVisualizationBackend
from app.features.detection_visualization.domain import (
    BACKEND_OPENCV,
    BACKEND_OPENCV_CPU_RESIZE,
    VISUALIZATION_BACKEND_DISPLAY_NAMES,
    default_visualization_config,
    get_config_section,
)

log = logging.getLogger(__name__)


def _opencv_has_gui() -> bool:
    """Проверка, что OpenCV собран с поддержкой GUI (imshow/namedWindow). Иначе превью детекции не покажется."""
    try:
        cv2.namedWindow("__gui_check__", cv2.WINDOW_NORMAL)
        cv2.destroyWindow("__gui_check__")
        return True
    except Exception:
        return False


def _resize_for_preview_opencv(
    img: np.ndarray, max_w: int, max_h: int, use_cuda: bool = True
) -> np.ndarray:
    """Ресайз под превью. max_w/max_h <= 0: без ресайза (качество как в источнике)."""
    h, w = img.shape[:2]
    if max_w <= 0 or max_h <= 0:
        return np.ascontiguousarray(img)
    if w <= max_w and h <= max_h:
        return np.ascontiguousarray(img)
    r = min(max_w / w, max_h / h)
    nw, nh = int(w * r), int(h * r)
    if use_cuda:
        try:
            cuda = getattr(cv2, "cuda", None)
            if cuda is not None and cuda.getCudaEnabledDeviceCount() > 0:
                gpu = cuda.GpuMat()
                gpu.upload(img)
                gpu_resized = cuda.resize(gpu, (nw, nh))
                return gpu_resized.download()
        except Exception:
            import logging

            logging.getLogger(__name__).debug("OpenCV window operation failed", exc_info=True)
    return cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)


class OpenCVBackend(IVisualizationBackend):
    """Отрисовка через OpenCV: resize (CPU или cv2.cuda) + imshow. Варианты по backend_id."""

    def __init__(self, backend_id: str = BACKEND_OPENCV) -> None:
        self._backend_id = (
            backend_id if backend_id in VISUALIZATION_BACKEND_DISPLAY_NAMES else BACKEND_OPENCV
        )
        section = get_config_section(self._backend_id)
        self._settings = default_visualization_config().get(section, {}).copy()
        self._display_thread: Thread | None = None
        self._running = False

    def get_id(self) -> str:
        return self._backend_id

    def get_display_name(self) -> str:
        return VISUALIZATION_BACKEND_DISPLAY_NAMES.get(
            self._backend_id, "OpenCV (GDI/mss + imshow)"
        )

    def get_default_settings(self) -> dict[str, Any]:
        use_cuda = self._backend_id != BACKEND_OPENCV_CPU_RESIZE
        capture = (
            "gdi"
            if self._backend_id == BACKEND_OPENCV_GDI
            else "mss"
            if self._backend_id == BACKEND_OPENCV_MSS
            else "gdi"
        )
        return {
            "preview_max_w": 0,
            "preview_max_h": 0,
            "use_cuda_resize": use_cuda,
            "capture_method": capture,
        }

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
                "key": "capture_method",
                "type": "choice",
                "label": "Метод захвата",
                "default": "gdi",
                "choices": ["gdi", "mss", "imshow"],
            },
        ]

    def get_settings(self) -> dict[str, Any]:
        return dict(self._settings)

    def apply_settings(self, settings: dict[str, Any]) -> None:
        self._settings.update(settings)

    def start_display(
        self,
        run_id: int,
        window_name: str,
        preview_queue: Queue,
        max_w: int,
        max_h: int,
        is_running_getter: Callable[[], bool],
        run_id_getter: Callable[[], int],
        on_stop: Callable[[], None] | None = None,
        on_q_key: Callable[[], None] | None = None,
        on_render_metrics: Callable[[float], None] | None = None,
    ) -> None:
        # Как в appv2: всегда запускаем поток отрисовки; при отсутствии GUI ошибка будет в display_loop
        max_w = self._settings.get("preview_max_w", max_w)
        max_h = self._settings.get("preview_max_h", max_h)
        use_cuda = self._settings.get("use_cuda_resize", True)

        # OpenCV на Windows нестабильно создаёт окна с пробелами в имени — используем только ASCII и run_id
        cv2_window_name = "YOLO_%d" % run_id

        def display_loop() -> None:
            self._running = True
            try:
                try:
                    cv2.startWindowThread()
                except Exception:
                    import logging

                    logging.getLogger(__name__).debug(
                        "OpenCV window operation failed", exc_info=True
                    )
                try:
                    cv2.destroyWindow(cv2_window_name)
                except Exception:
                    import logging

                    logging.getLogger(__name__).debug(
                        "OpenCV window operation failed", exc_info=True
                    )
                cv2.namedWindow(cv2_window_name, cv2.WINDOW_NORMAL)
                if max_w > 0 and max_h > 0:
                    cv2.resizeWindow(cv2_window_name, max_w, max_h)
            except cv2.error:
                log.exception("OpenCV backend: не удалось создать окно %s", cv2_window_name)
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
                    if (
                        img is not None
                        and isinstance(img, np.ndarray)
                        and img.dtype == np.uint8
                        and len(img.shape) == 3
                    ):
                        try:
                            t0 = time.perf_counter()
                            out = _resize_for_preview_opencv(img, max_w, max_h, use_cuda)
                            if out is not None:
                                out = np.ascontiguousarray(out)
                                cv2.imshow(cv2_window_name, out)
                            if on_render_metrics:
                                on_render_metrics((time.perf_counter() - t0) * 1000.0)
                        except Exception:
                            log.exception("Ошибка в display_loop (OpenCV resize/imshow)")
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

                        logging.getLogger(__name__).debug(
                            "OpenCV window operation failed", exc_info=True
                        )
                self._running = False
                if on_stop:
                    on_stop()

        self._display_thread = Thread(target=display_loop, daemon=True)
        self._display_thread.start()

    def stop_display(self) -> None:
        self._running = False
        t = self._display_thread
        self._display_thread = None
        if t is not None and t.is_alive():
            t.join(timeout=2.0)
