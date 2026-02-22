from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass
from multiprocessing.synchronize import Event as MpEvent
from typing import Generic, TypeVar

T = TypeVar("T")
ProgressFn = Callable[[float, str | None], None]
JobFn = Callable[["ProcessCancelToken", ProgressFn], T]


class ProcessCancelToken:
    def __init__(self, evt: MpEvent) -> None:
        self._evt = evt

    def cancel(self) -> None:
        self._evt.set()

    def is_cancelled(self) -> bool:
        return self._evt.is_set()


@dataclass(slots=True)
class ProcessJobHandle(Generic[T]):
    job_id: str
    name: str
    future: Future[T]
    cancel_evt: MpEvent

    def cancel(self) -> None:
        self.cancel_evt.set()
