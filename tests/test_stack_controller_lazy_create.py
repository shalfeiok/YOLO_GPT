from __future__ import annotations


def _import_qtwidgets_or_skip():
    import pytest

    pytest.importorskip("PySide6")
    try:
        from PySide6.QtWidgets import QApplication, QLabel, QStackedWidget
    except ImportError as exc:
        pytest.skip(f"PySide6 QtWidgets unavailable in this environment: {exc}")
    return QApplication, QLabel, QStackedWidget


def test_stack_controller_creates_tab_on_next_event_loop_tick() -> None:
    QApplication, QLabel, QStackedWidget = _import_qtwidgets_or_skip()

    from app.ui.shell.stack_controller import StackController

    app = QApplication.instance() or QApplication([])
    stack = QStackedWidget()

    created = {"count": 0}

    def _factory():
        created["count"] += 1
        return QLabel("ready")

    controller = StackController(stack, factories={"datasets": _factory})

    controller.switch_to("datasets")
    assert created["count"] == 0

    app.processEvents()
    assert created["count"] == 1


def test_stack_controller_renders_error_widget_when_factory_crashes() -> None:
    QApplication, QLabel, QStackedWidget = _import_qtwidgets_or_skip()

    from app.ui.shell.stack_controller import StackController

    app = QApplication.instance() or QApplication([])
    stack = QStackedWidget()

    def _boom():
        raise RuntimeError("factory failed")

    controller = StackController(stack, factories={"datasets": _boom})
    controller.switch_to("datasets")
    app.processEvents()

    labels = [w.text() for w in stack.currentWidget().findChildren(QLabel)]
    assert any("Ошибка загрузки вкладки" in t for t in labels)
    assert any("factory failed" in t for t in labels)
