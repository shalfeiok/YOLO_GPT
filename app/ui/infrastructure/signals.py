"""
Thread-safe signal bridge: worker threads emit progress and console lines to the main thread.
Use these QObject signals from callbacks/queue consumers so View can subscribe on main thread.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class TrainingSignals(QObject):
    """Signals for training progress and console output. Emit from any thread; slots run on main thread."""

    progress_updated = Signal(float, str)  # (0..1, status_message)
    console_line = Signal(str)  # one line of log (no newline); legacy, prefer console_lines_batch
    console_lines_batch = Signal(list)  # list[str] — batched for fewer UI updates
    training_finished = Signal(object, object)  # (best_path or None, error_str or None)
    training_stopped = Signal()


class DetectionSignals(QObject):
    """Signals for detection: FPS, stopped. Emit from worker thread."""

    fps_updated = Signal(float)
    detection_stopped = Signal()
