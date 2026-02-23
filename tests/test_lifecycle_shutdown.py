from __future__ import annotations

import types

import pytest


def _require_qt() -> None:
    pytest.importorskip("PySide6.QtWidgets", reason="PySide6 QtWidgets is required", exc_type=ImportError)


@pytest.mark.parametrize(
    "module_path,class_name,attrs",
    [
        (
            "app.ui.views.training.view",
            "TrainingView",
            {
                "_vm": types.SimpleNamespace(stop_training=lambda: None),
                "_container": types.SimpleNamespace(
                    event_bus=types.SimpleNamespace(unsubscribe=lambda _s: None)
                ),
                "_bus_subs": [],
                "_subscriptions": types.SimpleNamespace(dispose_all=lambda **_k: None),
                "_metrics_timer": None,
            },
        ),
        (
            "app.ui.views.jobs.view",
            "JobsView",
            {
                "_bus": types.SimpleNamespace(unsubscribe=lambda _s: None),
                "_subscriptions": types.SimpleNamespace(dispose_all=lambda **_k: None),
                "_subs": [],
            },
        ),
    ],
)
def test_shutdown_idempotent(module_path: str, class_name: str, attrs: dict[str, object]) -> None:
    _require_qt()
    module = __import__(module_path, fromlist=[class_name])
    cls = getattr(module, class_name)
    obj = cls.__new__(cls)
    for key, value in attrs.items():
        setattr(obj, key, value)

    obj.shutdown()
    obj.shutdown()


def test_shutdown_safe_on_partial_init_training_view() -> None:
    _require_qt()
    from app.ui.views.training.view import TrainingView

    obj = TrainingView.__new__(TrainingView)
    obj.shutdown()


def test_main_window_close_does_not_crash_when_tab_shutdown_fails() -> None:
    _require_qt()
    from PySide6.QtGui import QCloseEvent

    from app.ui.infrastructure.settings import AppSettings
    from app.ui.shell.main_window import MainWindow

    class _Tab:
        def shutdown(self) -> None:
            raise RuntimeError("boom")

    class _Stack:
        def count(self) -> int:
            return 1

        def widget(self, _index: int):
            return _Tab()

    window = MainWindow(settings=AppSettings(), container=None, signals=None)
    window._stack = _Stack()  # type: ignore[assignment]
    window.closeEvent(QCloseEvent())
