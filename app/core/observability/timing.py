"""Timing helpers for lightweight observability."""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

T = TypeVar("T")


@contextmanager
def time_block(
    name: str, *, logger: logging.Logger | None = None, level: int = logging.INFO
) -> Iterator[None]:
    log = logger or logging.getLogger(__name__)
    start = time.perf_counter()
    try:
        yield
    finally:
        dur_ms = (time.perf_counter() - start) * 1000
        log.log(level, "%s took %.1fms", name, dur_ms, extra={"event": "timing"})


def timed(name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to log execution time of a function."""

    def _decorator(fn: Callable[..., T]) -> Callable[..., T]:
        log = logging.getLogger(fn.__module__)

        @functools.wraps(fn)
        def _wrapped(*args: Any, **kwargs: Any) -> T:
            with time_block(name, logger=log):
                return fn(*args, **kwargs)

        return _wrapped

    return _decorator
