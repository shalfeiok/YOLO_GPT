"""
Domain for exporting YOLO model to various formats (ONNX, OpenVINO, TF, etc.).

Ref: https://docs.ultralytics.com/ru/guides/model-deployment-options/
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

EXPORT_FORMATS = [
    "torchscript",
    "onnx",
    "openvino",
    "engine",  # TensorRT
    "coreml",
    "saved_model",  # TensorFlow SavedModel
    "pb",  # TensorFlow GraphDef
    "tflite",
    "edgetpu",
    "tfjs",
    "paddle",
    "ncnn",
]


@dataclass
class ModelExportConfig:
    weights_path: str = ""
    format: str = "onnx"
    output_dir: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "weights_path": self.weights_path,
            "format": self.format,
            "output_dir": self.output_dir,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> ModelExportConfig:
        if not d:
            return cls()
        return cls(
            weights_path=str(d.get("weights_path", "")),
            format=str(d.get("format", "onnx")),
            output_dir=str(d.get("output_dir", "")),
        )
