"""
ONNX Runtime inference backend.

Uses the official API: InferenceSession (path, providers, sess_options),
session.run(output_names, input_feed), get_providers(), get_inputs().
See: https://onnxruntime.ai/docs/api/python/api_summary.html
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path
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

from app.yolo_inference.backends.base import AbstractModelBackend

log = logging.getLogger(__name__)

DEFAULT_INPUT_SIZE = 640

COCO_NAMES = (
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
)


def _prepend_cuda_paths_windows() -> None:
    """Prepend common CUDA/cuDNN bin paths to PATH so onnxruntime-gpu can load DLLs."""
    if sys.platform != "win32":
        return
    paths_to_add: list[str] = []
    cuda_root = (
        Path(os.environ.get("ProgramFiles", "C:\\Program Files"))
        / "NVIDIA GPU Computing Toolkit"
        / "CUDA"
    )
    if cuda_root.is_dir():
        for v in sorted(cuda_root.iterdir(), key=lambda p: p.name, reverse=True):
            bin_dir = v / "bin"
            if bin_dir.is_dir():
                paths_to_add.append(str(bin_dir))
                break
    cudnn_home = os.environ.get("CUDNN_PATH") or os.environ.get("CUDNN_HOME")
    if cudnn_home:
        bin_cudnn = Path(cudnn_home) / "bin"
        if bin_cudnn.is_dir():
            paths_to_add.append(str(bin_cudnn))
    if paths_to_add:
        existing = os.environ.get("PATH", "")
        os.environ["PATH"] = os.pathsep.join(paths_to_add) + os.pathsep + existing


def _is_cuda_dll_in_path() -> bool:
    """On Windows, check if key CUDA 12 DLL is in PATH to avoid loading CUDA provider and failing with a console error."""
    if sys.platform != "win32":
        return True
    path_env = os.environ.get("PATH", "")
    for part in path_env.split(os.pathsep):
        if not part:
            continue
        dll = Path(part) / "cublasLt64_12.dll"
        if dll.is_file():
            return True
        dll13 = Path(part) / "cublasLt64_13.dll"
        if dll13.is_file():
            return True
    return False


def _get_provider_candidates(skip_cuda_if_unavailable: bool = False) -> tuple[list[str], list[str]]:
    """
    Return (gpu_providers, cpu_providers) using ort.get_available_providers().
    If skip_cuda_if_unavailable is True (e.g. on Windows when CUDA DLL not in PATH),
    CUDA is not added to the list so ORT won't try to load it and print an error.
    """
    try:
        import onnxruntime as ort

        available = ort.get_available_providers()
    except ImportError:
        return ([], ["CPUExecutionProvider"])
    if sys.platform == "win32":
        gpu_order = ("DmlExecutionProvider", "CUDAExecutionProvider")
    elif sys.platform == "darwin":
        gpu_order = ("CoreMLExecutionProvider", "CUDAExecutionProvider")
    else:
        gpu_order = ("CUDAExecutionProvider",)
    gpu = [p for p in gpu_order if p in available]
    if skip_cuda_if_unavailable and "CUDAExecutionProvider" in gpu and not _is_cuda_dll_in_path():
        gpu = [p for p in gpu if p != "CUDAExecutionProvider"]
    cpu = ["CPUExecutionProvider"] if "CPUExecutionProvider" in available else []
    return (gpu, cpu)


def _parse_input_size(session: Any) -> int:
    """Infer input size from session.get_inputs()[0].shape (e.g. [1, 3, 640, 640] -> 640)."""
    try:
        inp = session.get_inputs()[0]
        shape = inp.shape
        if len(shape) >= 4:
            for i in (2, 3):
                dim = shape[i]
                if isinstance(dim, int) and dim > 0:
                    return dim
    except Exception:
        import logging

        logging.getLogger(__name__).debug("ONNX backend operation failed", exc_info=True)
    return DEFAULT_INPUT_SIZE


def _letterbox(
    img: np.ndarray,
    target_size: int,
) -> tuple[np.ndarray, float, float, float, int, int, int, int]:
    h, w = img.shape[:2]
    scale = min(target_size / w, target_size / h)
    new_w = int(round(w * scale))
    new_h = int(round(h * scale))
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    pad_w = target_size - new_w
    pad_h = target_size - new_h
    pad_left = pad_w // 2
    pad_top = pad_h // 2
    pad_right = pad_w - pad_left
    pad_bottom = pad_h - pad_top
    padded = cv2.copyMakeBorder(
        resized,
        pad_top,
        pad_bottom,
        pad_left,
        pad_right,
        cv2.BORDER_CONSTANT,
        value=(114, 114, 114),
    )
    return padded, scale, pad_left, pad_top, new_w, new_h, h, w


def _export_pt_to_onnx(weights_path: Path, imgsz: int = DEFAULT_INPUT_SIZE) -> Path:
    from ultralytics import YOLO

    model = YOLO(str(weights_path))
    out_path = model.export(
        format="onnx",
        imgsz=imgsz,
        dynamic=False,
        simplify=True,
        opset=12,
        half=False,
    )
    return Path(out_path)


def _get_color(class_id: int) -> tuple[int, int, int]:
    np.random.seed(class_id)
    return tuple(int(x) for x in np.random.uniform(0, 255, size=3))


class ONNXBackend(AbstractModelBackend):
    """
    ONNX Runtime inference backend.

    Creates InferenceSession with explicit providers (GPU then CPU fallback).
    Uses session.run([output names], input_feed) per official API.
    """

    def __init__(self) -> None:
        self._onnx_path: Path | None = None
        self._session: Any = None
        self._input_name: str | None = None
        self._input_size: int = DEFAULT_INPUT_SIZE
        self._providers: list[str] = []
        self._class_names: tuple[str, ...] = COCO_NAMES
        self._session_lock = threading.Lock()
        self._export_in_progress = False
        self._export_error: str | None = None

    def load(self, weights_path: Path) -> None:
        path = Path(weights_path)
        if not path.exists():
            raise FileNotFoundError(f"Weights not found: {path}")

        if path.suffix.lower() == ".onnx":
            self._load_session(path)
            return

        onnx_path = path.with_suffix(".onnx")
        if onnx_path.exists():
            self._load_session(onnx_path)
            return

        self._export_in_progress = True
        self._export_error = None

        def do_export() -> None:
            try:
                log.info("Exporting %s to ONNX: %s", path, onnx_path)
                _export_pt_to_onnx(path)
                self._load_session(onnx_path)
            except Exception as e:
                self._export_error = str(e)
                log.exception("ONNX export failed")
            finally:
                self._export_in_progress = False

        threading.Thread(target=do_export, daemon=True).start()

    def _load_session(self, onnx_path: Path) -> None:
        _prepend_cuda_paths_windows()
        with self._session_lock:
            self._onnx_path = onnx_path
            # On Windows skip CUDA in the list if DLL not in PATH to avoid ORT console error
            gpu_providers, cpu_providers = _get_provider_candidates(
                skip_cuda_if_unavailable=(sys.platform == "win32")
            )
            import onnxruntime as ort

            sess_options = ort.SessionOptions()
            path_str = str(onnx_path)
            self._session = None
            self._providers = []

            for candidate in (gpu_providers, cpu_providers):
                if not candidate:
                    continue
                try:
                    # InferenceSession(path, sess_options, providers) per API
                    self._session = ort.InferenceSession(
                        path_str,
                        sess_options=sess_options,
                        providers=candidate,
                    )
                    # get_providers() returns the list of registered execution providers
                    self._providers = list(self._session.get_providers())
                    log.info("ONNX session created with providers: %s", self._providers)
                    break
                except Exception as e:
                    log.warning("ONNX session with %s failed: %s", candidate, e)
                    continue

            if self._session is None:
                raise RuntimeError("Could not create ONNX session with any provider (GPU or CPU).")

            # get_inputs() returns list of NodeArg; we need name and shape
            self._input_name = self._session.get_inputs()[0].name
            self._input_size = _parse_input_size(self._session)
            log.info("ONNX input size: %d (from model)", self._input_size)

            if self._providers == ["CPUExecutionProvider"]:
                hint = (
                    "pip install onnxruntime-directml"
                    if sys.platform == "win32"
                    else "pip install onnxruntime-gpu (requires CUDA 12 + cuDNN 9)"
                )
                log.info("ONNX using CPU only; for GPU: %s", hint)

    def is_exporting(self) -> bool:
        return self._export_in_progress

    def get_export_error(self) -> str | None:
        return self._export_error

    def unload_model(self) -> None:
        with self._session_lock:
            self._session = None
            self._input_name = None
            self._onnx_path = None

    def _run_inference(self, blob: np.ndarray) -> np.ndarray:
        with self._session_lock:
            session, iname = self._session, self._input_name
        if session is None or iname is None:
            return np.zeros((1, 84, 0), dtype=np.float32)
        # session.run(output_names, input_feed) — None = all outputs
        outputs = session.run(None, {iname: blob})
        return outputs[0]

    def predict(
        self,
        frame: np.ndarray,
        conf: float = 0.45,
        iou: float = 0.45,
    ) -> tuple[np.ndarray, list[Any]]:
        with self._session_lock:
            if self._session is None:
                return frame, []
            inp_sz = self._input_size
        orig_h, orig_w = frame.shape[:2]
        padded, scale, pad_left, pad_top, new_w, new_h, _, _ = _letterbox(frame, inp_sz)
        blob = cv2.dnn.blobFromImage(
            padded,
            scalefactor=1.0 / 255.0,
            size=(inp_sz, inp_sz),
            swapRB=True,
            crop=False,
        )
        blob = blob.astype(np.float32)

        out = self._run_inference(blob)
        if out.size == 0:
            return frame, []

        sh = out.shape
        use_six_col = len(sh) == 3 and sh[2] == 6
        if use_six_col:
            num_proposals = sh[1]
            output = out[0]
        else:
            num_proposals = sh[2]
            output = np.transpose(out, (0, 2, 1))[0]

        boxes_list: list[list[float]] = []
        scores_list: list[float] = []
        class_ids_list: list[int] = []

        for i in range(num_proposals):
            row = output[i]
            if use_six_col:
                cx, cy, w, h = float(row[0]), float(row[1]), float(row[2]), float(row[3])
                score = float(row[4])
                class_id = int(row[5])
                if score < conf:
                    continue
                x1 = cx - 0.5 * w
                y1 = cy - 0.5 * h
                boxes_list.append([x1, y1, w, h])
                scores_list.append(score)
                class_ids_list.append(class_id)
            else:
                class_scores = row[4:]
                max_score = float(np.max(class_scores))
                if max_score < conf:
                    continue
                max_class_id = int(np.argmax(class_scores))
                cx, cy, w, h = row[0], row[1], row[2], row[3]
                x1 = float(cx - 0.5 * w)
                y1 = float(cy - 0.5 * h)
                boxes_list.append([x1, y1, float(w), float(h)])
                scores_list.append(max_score)
                class_ids_list.append(max_class_id)

        if not boxes_list:
            return frame, []

        nms_out = cv2.dnn.NMSBoxes(boxes_list, scores_list, conf, iou, 0.5)
        indices = (
            np.array(nms_out).flatten() if nms_out is not None else np.array([], dtype=np.int32)
        )
        if len(indices) == 0:
            return frame, []

        scale_back = 1.0 / scale
        annotated = frame.copy()

        for idx in indices:
            idx = int(idx)
            x1_640, y1_640, w_640, h_640 = boxes_list[idx]
            x1_l = (x1_640 - pad_left) * scale_back
            y1_l = (y1_640 - pad_top) * scale_back
            x2_l = (x1_640 + w_640 - pad_left) * scale_back
            y2_l = (y1_640 + h_640 - pad_top) * scale_back
            x1_i = max(0, min(orig_w, int(round(x1_l))))
            y1_i = max(0, min(orig_h, int(round(y1_l))))
            x2_i = max(0, min(orig_w, int(round(x2_l))))
            y2_i = max(0, min(orig_h, int(round(y2_l))))
            if x2_i <= x1_i or y2_i <= y1_i:
                continue
            score = scores_list[idx]
            class_id = class_ids_list[idx]
            name = (
                self._class_names[class_id] if class_id < len(self._class_names) else str(class_id)
            )
            label = f"{name} {score:.2f}"
            color = _get_color(class_id)
            cv2.rectangle(annotated, (x1_i, y1_i), (x2_i, y2_i), color, 2)
            cv2.putText(
                annotated,
                label,
                (x1_i, y1_i - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA,
            )

        results = [{"boxes": boxes_list, "scores": scores_list, "class_ids": class_ids_list}]
        return annotated, results

    @property
    def is_loaded(self) -> bool:
        with self._session_lock:
            return self._session is not None
