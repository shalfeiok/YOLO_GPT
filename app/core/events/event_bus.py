#commit и версия
from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from typing import Any, TypeVar, cast
from weakref import WeakMethod

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Subscription:
    event_type: type[object]
    handler: Callable[[object], None]


TEvent = TypeVar("TEvent")


class EventBus:
    """Simple, synchronous, in-process event bus.

    - Thread-safe subscribe/unsubscribe/publish.
    - Handlers are called synchronously in the publisher's thread.
      (UI can re-dispatch to the main thread if needed.)
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._subs: defaultdict[type[object], list[Callable[[object], None]]] = defaultdict(list)

    def subscribe(
        self, event_type: type[TEvent], handler: Callable[[TEvent], None]
    ) -> Subscription:
        # Internally we store object-based handlers; we adapt typed handlers
        # via a small wrapper so type-checking remains clean under stricter settings.
        def _wrapped(event: object) -> None:
            handler(cast(TEvent, event))

        with self._lock:
            self._subs[event_type].append(_wrapped)
        return Subscription(event_type=event_type, handler=_wrapped)

    def subscribe_weak(
        self, event_type: type[TEvent], handler: Callable[[TEvent], None]
    ) -> Subscription:
        """Subscribe with a weak reference when possible.

        Intended for UI objects (Qt widgets/view-models). If the owner is garbage-collected,
        the subscription is automatically removed on the next publish.
        """

        wm: WeakMethod | None
        try:
            # Only bound methods are supported by WeakMethod; others raise TypeError.
            wm = WeakMethod(cast(Any, handler))
        except TypeError:
            wm = None

        if wm is None:
            return self.subscribe(event_type, handler)

        sub: Subscription

        def _wrapped(event: object) -> None:
            alive = wm()
            if alive is None:
                self.unsubscribe(sub)
                return
            alive(cast(TEvent, event))

        sub = Subscription(event_type=event_type, handler=_wrapped)
        with self._lock:
            self._subs[event_type].append(_wrapped)
        return sub

    def unsubscribe(self, subscription: Subscription) -> None:
        with self._lock:
            handlers = self._subs.get(subscription.event_type)
            if not handlers:
                return
            try:
                handlers.remove(subscription.handler)
            except ValueError:
                return

    def publish(self, event: object) -> None:
        # Copy handlers under lock, then execute outside the lock.
        with self._lock:
            handlers = list(self._subs.get(type(event), []))
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Event handler failed",
                    extra={"event_type": type(event).__name__, "handler": repr(handler)},
                )

    def clear(self) -> None:
        """Remove all subscriptions."""
        with self._lock:
            self._subs.clear()
