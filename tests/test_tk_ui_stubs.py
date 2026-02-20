from __future__ import annotations

import importlib

import pytest


TK_STUB_MODULES = [
    "app.features.albumentations_integration.ui",
    "app.features.comet_integration.ui",
    "app.features.detection_visualization.ui",
    "app.features.dvc_integration.ui",
    "app.features.guides_launchers.ui",
    "app.features.hyperparameter_tuning.ui",
    "app.features.kfold_integration.ui",
    "app.features.model_export.ui",
    "app.features.model_validation.ui",
    "app.features.sagemaker_integration.ui",
    "app.features.sahi_integration.ui",
    "app.features.segmentation_isolation.ui",
    "app.features.ultralytics_solutions.ui",
]


@pytest.mark.parametrize("module_name", TK_STUB_MODULES)
def test_tk_ui_module_is_stub(module_name: str) -> None:
    mod = importlib.import_module(module_name)
    with pytest.raises(RuntimeError) as exc:
        mod.launch()
    msg = str(exc.value)
    assert "examples/tk_ui" in msg
    assert "PySide6" in msg
