"""Model backends for detection: PyTorch (Ultralytics) and ONNX Runtime (Part 4.10)."""
from app.yolo_inference.backends.base import AbstractModelBackend
from app.yolo_inference.backends.pytorch_backend import PyTorchBackend
from app.yolo_inference.backends.onnx_backend import ONNXBackend

__all__ = ["AbstractModelBackend", "PyTorchBackend", "ONNXBackend"]
