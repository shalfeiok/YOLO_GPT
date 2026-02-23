from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


class GuardedStoreUpdate:
    """Tracks store->UI apply phase to ignore recursive UI change events."""

    def __init__(self) -> None:
        self._applying_store_state = False

    @contextmanager
    def applying(self) -> Iterator[None]:
        previous = self._applying_store_state
        self._applying_store_state = True
        try:
            yield
        finally:
            self._applying_store_state = previous

    def should_ignore_user_change(self) -> bool:
        return self._applying_store_state
