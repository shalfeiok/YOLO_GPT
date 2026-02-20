from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class SupportsUnloadModel(Protocol):
    def unload_model(self) -> None: ...


@dataclass(frozen=True, slots=True)
class StopDetectionRequest:
    detector: object | None
    release_cuda_cache: bool = True


class StopDetectionError(RuntimeError):
    pass


class StopDetectionUseCase:
    """
    Stop/cleanup logic that must not live in UI.

    Responsibilities:
    - Unload model (best-effort)
    - Optionally release CUDA cache (best-effort)
    - Idempotent: safe to call multiple times
    """

    def execute(self, request: StopDetectionRequest) -> None:
        detector = request.detector
        if detector is not None and isinstance(detector, SupportsUnloadModel):
            try:
                detector.unload_model()
            except Exception as e:  # noqa: BLE001
                raise StopDetectionError(f"Не удалось выгрузить модель: {e}") from e

        if request.release_cuda_cache:
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                # Best-effort only; do not break stop.
                pass
