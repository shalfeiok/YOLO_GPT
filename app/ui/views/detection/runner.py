from __future__ import annotations

import logging
import time
from queue import Empty
from threading import Event, Lock, Thread
from typing import Callable, Optional

from app.config import PREVIEW_MAX_SIZE
from app.features.detection_visualization import get_backend
from app.features.detection_visualization.domain import get_config_section, use_gpu_tensor_for_preview
from app.features.detection_visualization.frame_buffers import FrameSlot, PreviewBuffer

log = logging.getLogger(__name__)

CV2_WIN_NAME = "YOLO Detection"
FRAME_QUEUE_GET_TIMEOUT_S = 0.03


class DetectionMetrics:
    """
    Atomic, thread-safe metrics; single lock. Hot-path setters write floats only.
    """

    __slots__ = ("_capture_ms", "_inference_ms", "_render_ms", "_lock")

    def __init__(self) -> None:
        self._capture_ms: float = 0.0
        self._inference_ms: float = 0.0
        self._render_ms: float = 0.0
        self._lock = Lock()

    def set_capture_ms(self, ms: float) -> None:
        with self._lock:
            self._capture_ms = ms

    def set_inference_ms(self, ms: float) -> None:
        with self._lock:
            self._inference_ms = ms

    def set_render_ms(self, ms: float) -> None:
        with self._lock:
            self._render_ms = ms

    def get_metrics(self) -> dict[str, float]:
        with self._lock:
            return {
                "capture_ms": self._capture_ms,
                "inference_ms": self._inference_ms,
                "render_ms": self._render_ms,
            }


class DetectionRunner:
    """
    Owns detection pipeline lifecycle: capture thread + inference thread + visualization backend display.
    UI must not manage threads directly.

    The runner is intentionally UI-agnostic: it exposes callbacks for stop and status updates.
    """

    def __init__(
        self,
        window_capture,
        create_frame_source: Callable[[object], object],
    ) -> None:
        self._window_capture = window_capture
        self._create_frame_source = create_frame_source

        self._run_event: Event = Event()
        self._capture_thread: Thread | None = None
        self._inference_thread: Thread | None = None

        self._opencv_source = None
        self._frame_slot: FrameSlot = FrameSlot()
        self._preview_buffer: PreviewBuffer = PreviewBuffer()
        self._metrics = DetectionMetrics()

        self._run_id = 0
        self._active_detector = None
        self._visualization_backend = None

    @property
    def metrics(self) -> DetectionMetrics:
        return self._metrics

    @property
    def preview_buffer(self) -> PreviewBuffer:
        return self._preview_buffer

    @property
    def is_running(self) -> bool:
        return self._run_event.is_set()

    @property
    def run_id(self) -> int:
        return self._run_id

    @property
    def active_detector(self):
        return self._active_detector

    def reset_source(self) -> None:
        """Release current cv2-like source if any."""
        if self._opencv_source is not None:
            try:
                self._opencv_source.release()
            except Exception:
                log.debug("Failed to release source", exc_info=True)
            self._opencv_source = None

    def stop(self, join_timeout_s: float = 2.0) -> None:
        """Stop threads and backend display; idempotent."""
        self._run_event.clear()
        self.reset_source()

        for th in (self._capture_thread, self._inference_thread):
            if th is not None and th.is_alive():
                th.join(timeout=join_timeout_s)
        self._capture_thread = None
        self._inference_thread = None

        try:
            if self._visualization_backend is not None:
                getattr(self._visualization_backend, "stop_display", lambda: None)()
        except Exception:
            log.debug("stop_display failed", exc_info=True)

    def configure_source(
        self,
        source_kind: str,
        *,
        hwnd: int | None = None,
        use_full_screen: bool = False,
        camera_index: int = 0,
        video_path: str | None = None,
    ) -> None:
        """
        Configure capture source. Does not start threads.
        source_kind: "screen" | "window" | "camera" | "video"
        """
        self.reset_source()
        if source_kind == "camera":
            self._opencv_source = self._create_frame_source(camera_index)
            if not getattr(self._opencv_source, "is_opened", lambda: False)():
                raise RuntimeError("Не удалось открыть камеру.")
        elif source_kind == "video":
            if not video_path:
                raise RuntimeError("Не указан путь к видео.")
            self._opencv_source = self._create_frame_source(video_path)
            if not getattr(self._opencv_source, "is_opened", lambda: False)():
                raise RuntimeError(f"Не удалось открыть видео: {video_path}")
        else:
            # screen/window: no cv2 source, captured via window_capture
            self._opencv_source = None

    def start_pipeline(
        self,
        *,
        detector,
        conf_f: float,
        iou_f: float,
        backend_id: str,
        vis_config: dict,
        source_kind: str,
        hwnd: int | None,
        use_full_screen: bool,
        on_stop: Callable[[int], None],
        on_status: Callable[[str], None],
    ) -> int:
        """
        Start full pipeline. Returns run_id.
        """
        # ensure clean previous run
        self.stop(join_timeout_s=0.5)

        self._active_detector = detector
        self._run_id += 1
        run_id = self._run_id

        self._frame_slot.clear()
        self._preview_buffer.clear()
        self._run_event.set()

        # backend display
        self._visualization_backend = get_backend(backend_id)
        section = get_config_section(backend_id)
        self._visualization_backend.apply_settings(vis_config.get(section, {}))

        window_name = f"{CV2_WIN_NAME} {run_id}"

        def _on_render_metrics(ms: float) -> None:
            self._metrics.set_render_ms(ms)

        # visualization backend invokes callbacks from its own thread; keep callbacks lightweight
        self._visualization_backend.start_display(
            run_id=run_id,
            window_name=window_name,
            preview_queue=self._preview_buffer,
            max_w=PREVIEW_MAX_SIZE[0],
            max_h=PREVIEW_MAX_SIZE[1],
            is_running_getter=lambda: self._run_event.is_set(),
            run_id_getter=lambda: self._run_id,
            on_stop=lambda: on_stop(run_id),
            on_q_key=lambda: self.stop(),
            on_render_metrics=_on_render_metrics,
        )

        on_status(f"Превью в окне «{CV2_WIN_NAME}». Нажмите Стоп или Q в окне превью для остановки.")

        # threads
        if source_kind in ("camera", "video"):
            self._capture_thread = Thread(target=self._capture_loop, name=f"detection-capture-{run_id}", daemon=True)
            self._capture_thread.start()
        else:
            # window/screen capture in inference loop (pull based); nothing to do here
            pass

        self._inference_thread = Thread(
            target=self._inference_loop,
            name=f"detection-infer-{run_id}",
            kwargs=dict(
                conf_f=conf_f,
                iou_f=iou_f,
                backend_id=backend_id,
                source_kind=source_kind,
                hwnd=hwnd,
                use_full_screen=use_full_screen,
            ),
            daemon=True,
        )
        self._inference_thread.start()
        return run_id

    def _capture_loop(self) -> None:
        try:
            while self._run_event.is_set() and self._opencv_source is not None:
                t0 = time.perf_counter()
                ret, frame = self._opencv_source.read()
                self._metrics.set_capture_ms((time.perf_counter() - t0) * 1000.0)
                if not ret:
                    time.sleep(0.1)
                    continue
                if frame is not None:
                    self._frame_slot.put_nowait(frame)
                time.sleep(0.03)
        except Exception:
            log.exception("capture_loop")

    def _inference_loop(
        self,
        *,
        conf_f: float,
        iou_f: float,
        backend_id: str,
        source_kind: str,
        hwnd: int | None,
        use_full_screen: bool,
    ) -> None:
        import numpy as np

        use_gpu_tensor = use_gpu_tensor_for_preview(backend_id)

        def _put_preview(img: np.ndarray) -> None:
            if img is None or img.dtype != np.uint8 or len(img.shape) != 3:
                return
            if use_gpu_tensor:
                try:
                    import torch
                    if torch.cuda.is_available():
                        payload = torch.from_numpy(img).cuda()
                    else:
                        payload = img
                except Exception:
                    payload = img
            else:
                payload = img
            self._preview_buffer.put_nowait(payload)

        # warm-up
        getattr(self._active_detector, "ensure_model_ready", lambda: None)()

        try:
            while self._run_event.is_set() and getattr(self._active_detector, "is_loaded", True):
                # fetch frame
                if source_kind in ("camera", "video"):
                    try:
                        frame = self._frame_slot.get(timeout=FRAME_QUEUE_GET_TIMEOUT_S)
                    except Empty:
                        continue
                else:
                    t0 = time.perf_counter()
                    if source_kind == "screen":
                        frame = self._window_capture.capture_screen() if use_full_screen else None
                    else:
                        frame = self._window_capture.capture_window(hwnd) if hwnd is not None else None
                    self._metrics.set_capture_ms((time.perf_counter() - t0) * 1000.0)
                    if frame is None:
                        time.sleep(0.03)
                        continue

                t_infer_start = time.perf_counter()
                try:
                    annotated, _ = self._active_detector.predict(frame, conf=conf_f, iou=iou_f)
                except Exception:
                    log.warning("predict failed", exc_info=True)
                    annotated = frame
                self._metrics.set_inference_ms((time.perf_counter() - t_infer_start) * 1000.0)

                if annotated is None or not hasattr(annotated, "shape") or len(annotated.shape) < 3:
                    continue
                _put_preview(annotated)
        except Exception:
            log.exception("inference_loop")
        finally:
            # ensure the event is cleared when loop exits
            self._run_event.clear()
