"""
Apply Comet ML env vars before training so Ultralytics callback picks them up.

Ref: https://docs.ultralytics.com/ru/integrations/comet/
"""

import os

from app.features.comet_integration.domain import CometConfig


def apply_comet_env(config: CometConfig) -> dict[str, str]:
    """
    Set COMET_* env vars for current process. Returns previous values so caller can restore.
    Ultralytics checks COMET_API_KEY and COMET_PROJECT_NAME etc.
    """
    prev: dict[str, str] = {}
    if config.enabled and config.api_key:
        keys = [
            ("COMET_API_KEY", config.api_key),
            ("COMET_PROJECT_NAME", config.project_name),
            ("COMET_MAX_IMAGE_PREDICTIONS", str(config.max_image_predictions)),
            ("COMET_EVAL_BATCH_LOGGING_INTERVAL", str(config.eval_batch_logging_interval)),
            ("COMET_EVAL_LOG_CONFUSION_MATRIX", "1" if config.eval_log_confusion_matrix else "0"),
            ("COMET_MODE", config.mode),
        ]
        for k, v in keys:
            prev[k] = os.environ.get(k, "")
            os.environ[k] = v
    return prev


def restore_comet_env(prev: dict[str, str]) -> None:
    """Restore COMET_* env vars from previous snapshot."""
    for k, v in prev.items():
        if v == "":
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
