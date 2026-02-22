from __future__ import annotations

import contextlib
import importlib
import importlib.abc
import sys
from collections.abc import Iterable


class _Blocker(importlib.abc.MetaPathFinder):
    def __init__(self, blocked: set[str]):
        self.blocked = blocked

    def find_spec(self, fullname, path, target=None):
        root = fullname.split(".")[0]
        if root in self.blocked:
            raise ImportError(f"Blocked optional dependency for test: {root}")
        return None


@contextlib.contextmanager
def _blocked_imports(blocked: Iterable[str]):
    blocked_set = set(blocked)
    blocker = _Blocker(blocked_set)
    sys.meta_path.insert(0, blocker)
    removed = {}
    for name in list(sys.modules.keys()):
        root = name.split(".")[0]
        if root in blocked_set:
            removed[name] = sys.modules.pop(name)
    try:
        yield
    finally:
        if sys.meta_path and sys.meta_path[0] is blocker:
            sys.meta_path.pop(0)
        sys.modules.update(removed)


def test_imports_without_cv2_ultralytics_albumentations_comet():
    blocked = {"cv2", "ultralytics", "albumentations", "comet_ml"}
    modules = [
        "app",
        "app.services.capture_service",
        "app.services.dataset_augment_service",
        "app.services.dataset_visualize",
        "app.yolo_inference.backends.pytorch_backend",
        "app.yolo_inference.backends.onnx_backend",
        "app.features.ultralytics_solutions.service",
        "app.features.segmentation_isolation.service",
        "app.features.detection_visualization.backends.opencv_backend",
    ]
    with _blocked_imports(blocked):
        for m in modules:
            importlib.import_module(m)
