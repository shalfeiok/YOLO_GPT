import pytest

qt_widgets = pytest.importorskip("PySide6.QtWidgets")
QApplication = qt_widgets.QApplication

from app.ui.infrastructure.settings import AppSettings
from app.ui.shell.main_window import MainWindow


def test_main_window_can_be_created_without_container() -> None:
    app = QApplication.instance() or QApplication([])
    w = MainWindow(settings=AppSettings(), container=None, signals=None)
    assert w.windowTitle()
    w.close()
    app.quit()
