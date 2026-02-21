from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, cast

from app.core.events.job_events import (
    JobCancelled,
    JobFailed,
    JobFinished,
    JobLogLine,
    JobProgress,
    JobRetrying,
    JobStarted,
    JobTimedOut,
)

JobEvent = (
    JobStarted
    | JobProgress
    | JobLogLine
    | JobFinished
    | JobFailed
    | JobCancelled
    | JobRetrying
    | JobTimedOut
)


class JobEventStore(Protocol):
    def load(self) -> list[dict[str, Any]]:
        """Load previously stored events."""

    def append(self, event: dict[str, Any]) -> None:
        """Append a single event record."""

    def clear(self) -> None:
        """Clear all stored events."""


class JsonlJobEventStore:
    """Append-only JSONL store for Job* events.

    Stores one JSON object per line. Designed to be resilient:
    - ignores malformed lines on load
    - creates parent dirs automatically
    """

    def __init__(
        self,
        path: Path,
        *,
        max_bytes: int = 5 * 1024 * 1024,
        max_archives: int = 5,
    ) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._max_bytes = int(max_bytes)
        self._max_archives = int(max_archives)

    def _rotate_if_needed(self) -> None:
        try:
            if not self._path.exists():
                return
            if self._max_bytes <= 0:
                return
            if self._path.stat().st_size <= self._max_bytes:
                return

            ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            rotated = self._path.with_name(f"{self._path.stem}.{ts}{self._path.suffix}")
            self._path.replace(rotated)

            # Purge old archives
            archives = sorted(
                self._path.parent.glob(f"{self._path.stem}.*{self._path.suffix}"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for p in archives[self._max_archives :]:
                try:
                    p.unlink()
                except Exception:
                    continue
        except Exception:
            return

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        out: list[dict[str, Any]] = []
        try:
            with self._path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict) and "type" in obj and "data" in obj:
                            out.append(obj)
                    except Exception:
                        continue
        except Exception:
            return []
        return out

    def append(self, event: dict[str, Any]) -> None:
        try:
            self._rotate_if_needed()
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            # Persistence should never crash the app.
            return

    def clear(self) -> None:
        try:
            if self._path.exists():
                self._path.unlink()
        except Exception:
            return


def _safe_serialize(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _safe_serialize(v) for k, v in asdict(cast(Any, value)).items()}
    if isinstance(value, dict):
        return {str(k): _safe_serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_serialize(v) for v in value]
    # Fallback: short repr
    s = repr(value)
    return s[:1000]


def pack_job_event(e: JobEvent) -> dict[str, Any]:
    """Convert a Job* event instance to a JSON-serializable dict."""
    t = type(e).__name__
    raw: Any = asdict(cast(Any, e))
    data = _safe_serialize(raw)
    return {"type": t, "data": data, "ts": datetime.utcnow().isoformat()}
