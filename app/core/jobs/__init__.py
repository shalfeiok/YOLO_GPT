"""Background jobs infrastructure.

Provides a small, thread-based job runner for long-running tasks so the Qt UI
never blocks.
"""

from .job_event_store import JobEventStore, JsonlJobEventStore, pack_job_event
from .job_registry import JobRecord, JobRegistry
from .job_runner import CancelToken, JobHandle, JobRunner
from .process_job_runner import ProcessJobHandle, ProcessJobRunner

__all__ = [
    "CancelToken",
    "JobHandle",
    "JobRunner",
    "ProcessJobHandle",
    "ProcessJobRunner",
    "JobRecord",
    "JobRegistry",
    "JobEventStore",
    "JsonlJobEventStore",
    "pack_job_event",
]
