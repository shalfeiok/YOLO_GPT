"""
Low-overhead frame passing for the detection pipeline (capture → inference → preview).

Part 6.10: Minimal lock contention; drop-old-frame preserved; no race conditions.
- FrameSlot: deque(maxlen=1) auto-drops oldest on append; single lock for put/get.
- PreviewBuffer: write to slot then swap index under lock; consumer reads other slot.
"""

from __future__ import annotations

import threading
from collections import deque
from queue import Empty


class FrameSlot:
    """
    Single-frame slot with drop-old-frame semantics. Part 6.10: minimal critical section —
    append (deque maxlen=1 drops oldest); get waits on condition. No extra clear before put.
    """

    def __init__(self) -> None:
        self._deque: deque = deque(maxlen=1)
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)

    def put_nowait(self, frame) -> None:
        with self._lock:
            self._deque.append(frame)  # maxlen=1 drops previous frame
            self._cond.notify_all()

    def get(self, timeout: float | None = None):
        with self._cond:
            if not self._cond.wait_for(lambda: len(self._deque) > 0, timeout=timeout):
                raise Empty
            return self._deque.popleft()

    def get_nowait(self):
        with self._lock:
            if not self._deque:
                raise Empty
            return self._deque.popleft()

    def clear(self) -> None:
        with self._lock:
            self._deque.clear()


class PreviewBuffer:
    """
    Double-buffer for inference → display: no copy, no frame mutation race.
    Part 6.10: Only swap index and flag under lock; producer/consumer never touch same slot.
    """

    def __init__(self) -> None:
        self._buf: list = [None, None]
        self._write_slot = 0
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._has_data = False

    def put(self, frame) -> None:
        with self._lock:
            self._buf[self._write_slot] = frame
            self._write_slot = 1 - self._write_slot
            self._has_data = True
            self._cond.notify_all()  # single notify, minimal hold time

    def put_nowait(self, frame) -> None:
        self.put(frame)

    def get(self, timeout: float | None = None):
        with self._cond:
            if not self._cond.wait_for(lambda: self._has_data, timeout=timeout):
                raise Empty
            read_slot = 1 - self._write_slot
            return self._buf[read_slot]

    def get_nowait(self):
        with self._lock:
            if not self._has_data:
                raise Empty
            read_slot = 1 - self._write_slot
            return self._buf[read_slot]

    def clear(self) -> None:
        with self._lock:
            self._buf[0] = None
            self._buf[1] = None
            self._has_data = False
