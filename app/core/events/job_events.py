from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class JobStarted:
    job_id: str
    name: str


@dataclass(frozen=True, slots=True)
class JobProgress:
    job_id: str
    name: str
    progress: float  # 0..1
    message: str | None = None


@dataclass(frozen=True, slots=True)
class JobFinished:
    job_id: str
    name: str
    result: Any = None


@dataclass(frozen=True, slots=True)
class JobFailed:
    job_id: str
    name: str
    error: str


@dataclass(frozen=True, slots=True)
class JobRetrying:
    """Emitted when a job is about to be retried after a failure."""

    job_id: str
    name: str
    attempt: int  # 1-based
    max_attempts: int
    error: str


@dataclass(frozen=True, slots=True)
class JobTimedOut:
    """Emitted when a job exceeded its timeout and was cancelled cooperatively."""

    job_id: str
    name: str
    timeout_sec: float


@dataclass(frozen=True, slots=True)
class JobCancelled:
    job_id: str
    name: str


@dataclass(frozen=True, slots=True)
class JobLogLine:
    """A single log line produced by a background job.

    Intended for UI tail views.
    """

    job_id: str
    name: str
    line: str
