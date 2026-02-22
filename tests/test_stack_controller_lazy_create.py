from __future__ import annotations


def test_stack_controller_creates_tab_on_next_event_loop_tick() -> None:
    import pytest
    pytest.importorskip("PySide6")
    try:
        from PySide6.QtWidgets import QApplication, QLabel, QStackedWidget
    except ImportError as exc:
        pytest.skip(f"PySide6 QtWidgets unavailable in this environment: {exc}")

    from app.ui.shell.stack_controller import StackController

    app = QApplication.instance() or QApplication([])
    stack = QStackedWidget()

    created = {"count": 0}

    def _factory():
        created["count"] += 1
        return QLabel("ready")

    controller = StackController(stack, factories={"datasets": _factory})

    controller.switch_to("datasets")
    # Not yet created synchronously.
    assert created["count"] == 0

    app.processEvents()
    assert created["count"] == 1
