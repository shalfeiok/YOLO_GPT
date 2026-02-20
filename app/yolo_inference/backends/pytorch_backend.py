"""
PyTorch (Ultralytics YOLO) inference backend.

Model lifecycle (Part 1): Model is created only in the inference thread via
ensure_model_created_in_current_thread(), never lazily in predict(). load_model()
stores path and clears model; inference thread calls ensure_model_created_in_current_thread()
before the predict loop. Pre-warm runs one dummy inference to initialize CUDA kernels.
Thread ownership (Part 4.7): predict() may only be called from the registered inference thread.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, List, Optional, Tuple
try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None  # type: ignore



def _require_cv2() -> None:
    if cv2 is None:
        raise ImportError("OpenCV (cv2) is required for this feature. Install with: pip install opencv-python")
import numpy as np

from app.yolo_inference.backends.base import AbstractModelBackend


def _create_yolo_model(weights_path: Path) -> Any:
    from ultralytics import YOLO
    return YOLO(str(weights_path))


def _draw_boxes_cv2(
    frame: np.ndarray,
    xyxy: np.ndarray,
    confs: np.ndarray,
    class_ids: np.ndarray,
    names: dict[int, str],
) -> np.ndarray:
    """Draw bounding boxes and labels on a single frame copy. No r.plot() bottleneck (Part 2)."""
    out = frame.copy()
    for i in range(len(xyxy)):
        x1, y1, x2, y2 = map(int, xyxy[i])
        if x2 <= x1 or y2 <= y1:
            continue
        conf = float(confs[i])
        cid = int(class_ids[i])
        name = names.get(cid, str(cid))
        label = f"{name} {conf:.2f}"
        np.random.seed(cid)
        color = tuple(int(x) for x in np.random.uniform(0, 255, size=3))
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            out, label, (x1, y1 - 6),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA,
        )
    return out


class PyTorchBackend(AbstractModelBackend):
    """
    YOLO inference via Ultralytics. Model is created in inference thread only
    (ensure_model_created_in_current_thread); predict() never creates model.
    """

    def __init__(self) -> None:
        self._weights_path: Optional[Path] = None
        self._force_cpu: bool = False
        self._model: Any = None
        self._model_lock = threading.Lock()
        # Part 4.7: only the thread that created the model may call predict()
        self._inference_thread_id: Optional[int] = None

    def load(self, weights_path: Path) -> None:
        """Store path and clear model. Actual creation happens in inference thread."""
        path = Path(weights_path)
        if not path.exists():
            raise FileNotFoundError(f"Weights not found: {path}")
        with self._model_lock:
            self._weights_path = path
            self._force_cpu = False
            self._model = None
            self._inference_thread_id = None

    def ensure_model_created_in_current_thread(self) -> None:
        """
        Create model in the calling thread (must be inference thread) and pre-warm.
        Called once at start of inference loop; predict() never creates model (Part 1).
        """
        with self._model_lock:
            if self._weights_path is None or self._model is not None:
                return
            self._model = _create_yolo_model(self._weights_path)
            self._inference_thread_id = threading.current_thread().ident
        self._prewarm()

    def _prewarm(self) -> None:
        """One dummy inference to initialize CUDA kernels and avoid first-frame spike (Part 1.2)."""
        model = self._model
        if model is None:
            return
        try:
            import torch
            device = "cpu" if self._force_cpu else ("cuda" if torch.cuda.is_available() else "cpu")
            if device == "cuda":
                dummy = np.zeros((640, 640, 3), dtype=np.uint8)
                with torch.no_grad():
                    model.predict(source=dummy, conf=0.25, iou=0.45, device=device, verbose=False, stream=False)
        except Exception:
            import logging
            logging.getLogger(__name__).debug('PyTorch backend operation failed', exc_info=True)
    def _check_inference_thread(self) -> None:
        """Part 4.7: enforce single inference-thread ownership."""
        if self._inference_thread_id is None:
            return
        if threading.current_thread().ident != self._inference_thread_id:
            raise RuntimeError(
                "predict() may only be called from the registered inference thread. "
                "Ensure ensure_model_created_in_current_thread() was called from that thread."
            )

    def predict(
        self,
        frame: np.ndarray,
        conf: float = 0.45,
        iou: float = 0.45,
    ) -> Tuple[np.ndarray, List[Any]]:
        self._check_inference_thread()
        with self._model_lock:
            model = self._model
        if model is None:
            return frame, []
        device = "cpu" if self._force_cpu else None
        try:
            import torch
            with torch.no_grad():
                results = model.predict(
                    source=frame,
                    conf=conf,
                    iou=iou,
                    device=device,
                    verbose=False,
                    stream=False,
                )
        except RuntimeError as e:
            if not self._force_cpu and ("no kernel image" in str(e) or "CUDA" in str(e)):
                self._force_cpu = True
                import torch
                with torch.no_grad():
                    results = model.predict(
                        source=frame, conf=conf, iou=iou, device="cpu", verbose=False, stream=False
                    )
            else:
                raise
        if not results:
            return frame, []
        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return frame, results
        xyxy = r.boxes.xyxy.cpu().numpy()
        confs = r.boxes.conf.cpu().numpy()
        class_ids = r.boxes.cls.cpu().numpy()
        names = getattr(r, "names", None) or getattr(model, "names", {})
        if isinstance(names, list):
            names = {i: n for i, n in enumerate(names)}
        annotated = _draw_boxes_cv2(frame, xyxy, confs, class_ids, names)
        return annotated, results

    def unload_model(self) -> None:
        """Part 5.8: clear model reference and free GPU cache on stop."""
        with self._model_lock:
            self._model = None
            self._inference_thread_id = None
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            import logging
            logging.getLogger(__name__).debug('PyTorch backend operation failed', exc_info=True)
    @property
    def is_loaded(self) -> bool:
        return self._weights_path is not None
