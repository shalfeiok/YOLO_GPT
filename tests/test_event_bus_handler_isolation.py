from __future__ import annotations

from dataclasses import dataclass

from app.core.events.event_bus import EventBus


@dataclass(frozen=True)
class _Evt:
    value: int


def test_publish_continues_when_one_handler_raises() -> None:
    bus = EventBus()
    received: list[int] = []

    def broken(_evt: _Evt) -> None:
        raise RuntimeError("boom")

    def healthy(evt: _Evt) -> None:
        received.append(evt.value)

    bus.subscribe(_Evt, broken)
    bus.subscribe(_Evt, healthy)

    bus.publish(_Evt(7))

    assert received == [7]
