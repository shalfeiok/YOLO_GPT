"""Lightweight in-process event bus.

The goal is to decouple application logic from UI. Use-cases publish domain/application
events; UI subscribes.
"""

from .event_bus import EventBus
from .events import (
    TrainingCancelled,
    TrainingFailed,
    TrainingFinished,
    TrainingProgress,
    TrainingStarted,
)
from .job_events import (
    JobCancelled,
    JobFailed,
    JobFinished,
    JobLogLine,
    JobProgress,
    JobRetrying,
    JobStarted,
    JobTimedOut,
)

__all__ = [
    "EventBus",
    "JobStarted",
    "JobProgress",
    "JobFinished",
    "JobFailed",
    "JobCancelled",
    "JobLogLine",
    "JobRetrying",
    "JobTimedOut",
    "TrainingStarted",
    "TrainingProgress",
    "TrainingFinished",
    "TrainingFailed",
    "TrainingCancelled",
]
