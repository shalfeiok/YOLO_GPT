from __future__ import annotations

from functools import lru_cache


def _torch_cuda_info() -> tuple[bool, list[str]]:
    try:
        import torch

        if not torch.cuda.is_available():
            return False, []
        count = int(torch.cuda.device_count())
        names: list[str] = []
        for idx in range(count):
            try:
                names.append(str(torch.cuda.get_device_name(idx)))
            except Exception:
                names.append("Unknown GPU")
        return True, names
    except Exception:
        return False, []


@lru_cache(maxsize=1)
def detect_devices() -> list[tuple[str, str]]:
    """Return device options as (value, label) for training UI.

    value is the normalized value that goes into TrainingSettings.device.
    """

    options: list[tuple[str, str]] = [("auto", "Auto"), ("cpu", "CPU")]
    has_cuda, names = _torch_cuda_info()
    if has_cuda:
        for idx, name in enumerate(names):
            options.append((str(idx), f"GPU {idx}: {name}"))
    return options


@lru_cache(maxsize=1)
def is_cuda_available() -> bool:
    has_cuda, _ = _torch_cuda_info()
    return has_cuda
