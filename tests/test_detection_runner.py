from __future__ import annotations

from app.ui.views.detection.runner import DetectionRunner


class _DummyCapture:
    def capture_window(self, hwnd):
        return None

    def capture_screen(self):
        return None


class _DummySource:
    def __init__(self):
        self.released = False

    def is_opened(self):
        return True

    def release(self):
        self.released = True


def test_runner_stop_is_idempotent():
    runner = DetectionRunner(window_capture=_DummyCapture(), create_frame_source=lambda spec: _DummySource())
    runner.stop()
    runner.stop()  # should not raise


def test_configure_source_camera_ok():
    runner = DetectionRunner(window_capture=_DummyCapture(), create_frame_source=lambda spec: _DummySource())
    runner.configure_source("camera", camera_index=0)
    runner.stop()
