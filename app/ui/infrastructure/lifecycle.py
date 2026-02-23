"""Lifecycle helpers for idempotent, best-effort shutdown."""

from __future__ import annotations

import logging
from collections.abc import Callable
from threading import Thread
from typing import Any

log = logging.getLogger(__name__)


class SubscriptionManager:
    """Tracks bus/signal subscriptions and disposers."""

    def __init__(self) -> None:
        self._subscriptions: list[Any] = []
        self._callbacks: list[Callable[[], None]] = []

    def add_subscription(self, subscription: Any) -> Any:
        self._subscriptions.append(subscription)
        return subscription

    def add_disposer(self, disposer: Callable[[], None]) -> Callable[[], None]:
        self._callbacks.append(disposer)
        return disposer

    def dispose_all(self, *, bus: Any | None = None, logger: logging.Logger | None = None) -> None:
        target_log = logger or log
        for disposer in list(self._callbacks):
            try:
                disposer()
            except Exception:
                target_log.exception("Failed to run disposer during shutdown")
        self._callbacks.clear()

        if bus is not None:
            for subscription in list(self._subscriptions):
                try:
                    bus.unsubscribe(subscription)
                except Exception:
                    target_log.exception("Failed to unsubscribe during shutdown")
        self._subscriptions.clear()


class ResourceGuard:
    """Best-effort stopping/releasing of runtime resources."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._log = logger or log

    def stop_timer(self, timer: Any | None) -> None:
        if timer is None:
            return
        try:
            if hasattr(timer, "isActive") and timer.isActive():
                timer.stop()
            elif hasattr(timer, "stop"):
                timer.stop()
        except Exception:
            self._log.exception("Failed to stop timer")

    def stop_thread(self, thread: Thread | None, *, timeout_s: float = 1.0) -> None:
        if thread is None:
            return
        try:
            if thread.is_alive():
                thread.join(timeout=timeout_s)
        except Exception:
            self._log.exception("Failed to stop thread")

    def release_capture(self, capture: Any | None) -> None:
        if capture is None:
            return
        try:
            if hasattr(capture, "release"):
                capture.release()
        except Exception:
            self._log.exception("Failed to release capture")
