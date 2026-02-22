"""App shell: main window, collapsible sidebar, stack controller, lazy tabs."""

from app.ui.shell.main_window import MainWindow
from app.ui.shell.sidebar import CollapsibleSidebar
from app.ui.shell.stack_controller import TAB_IDS, StackController

__all__ = ["MainWindow", "CollapsibleSidebar", "StackController", "TAB_IDS"]
