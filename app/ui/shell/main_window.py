"""
Main window: collapsible sidebar + stacked content, lazy tabs, keyboard navigation.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStatusBar, QStackedWidget, QWidget

from app.ui.components.command_palette import CommandPalette, run_id_to_tab
from app.ui.infrastructure.settings import AppSettings
from app.ui.theme.manager import THEME_DARK, THEME_LIGHT
from app.ui.shell.sidebar import CollapsibleSidebar, SIDEBAR_WIDTH_COLLAPSED, SIDEBAR_WIDTH_EXPANDED
from app.ui.shell.stack_controller import StackController, TAB_IDS
from app.core.version import get_version_string

if TYPE_CHECKING:
    from app.ui.infrastructure.di import Container
    from app.ui.infrastructure.signals import TrainingSignals


class MainWindow(QMainWindow):
    """Main application window: sidebar + content stack, geometry and sidebar state persisted."""

    def __init__(
        self,
        settings: AppSettings,
        container: Container | None = None,
        signals: TrainingSignals | None = None,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._container = container
        self.setWindowTitle(f"YOLO Desktop Studio — {get_version_string()}")
        self.setMinimumSize(900, 620)
        self.resize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar_collapsed = self._settings.get_sidebar_collapsed()
        self._sidebar = CollapsibleSidebar(self, initial_collapsed=sidebar_collapsed, container=container)
        self._sidebar.tab_changed.connect(self._on_tab_changed)

        self._stack = QStackedWidget()
        factories = None
        if container is not None and signals is not None:
            from app.ui.views.training.view import TrainingView
            from app.ui.views.detection.view import DetectionView
            from app.ui.views.datasets.view import DatasetsView
            from app.ui.views.integrations.view import IntegrationsView
            from app.ui.views.jobs.view import JobsView
            factories = {
                "training": lambda: TrainingView(container, signals),
                "detection": lambda: DetectionView(container),
                "datasets": lambda: DatasetsView(),
                "integrations": lambda: IntegrationsView(container),
                "jobs": lambda: JobsView(container),
            }
        else:
            factories = {}
        self._stack_controller = StackController(self._stack, factories=factories)
        self._stack_controller.switch_to(TAB_IDS[0])
        self._sidebar.set_current_tab(TAB_IDS[0])

        layout.addWidget(self._sidebar)
        layout.addWidget(self._stack, 1)

        theme_mgr = container.theme_manager if container else None
        if theme_mgr:
            theme_mgr.theme_changed.connect(self._on_theme_changed)

        self._command_palette = CommandPalette(self)
        self._command_palette.set_on_run(self._on_command_palette_run)
        status = QStatusBar(self)
        status.showMessage("Ctrl+K — палитра команд  |  Ctrl+1…5 — вкладки")
        self.setStatusBar(status)
        self._setup_shortcuts()
        self._restore_geometry()

    def _setup_shortcuts(self) -> None:
        for i, tab_id in enumerate(TAB_IDS):
            action = QAction(self)
            action.setShortcut(QKeySequence(f"Ctrl+{i + 1}"))
            action.triggered.connect(lambda checked=False, t=tab_id: self._on_tab_changed(t))
            self.addAction(action)
        palette_action = QAction(self)
        palette_action.setShortcut(QKeySequence("Ctrl+K"))
        palette_action.triggered.connect(self._open_command_palette)
        self.addAction(palette_action)

    def _open_command_palette(self) -> None:
        self._command_palette.exec()

    def _on_command_palette_run(self, command_id: str) -> None:
        tab_id = run_id_to_tab(command_id)
        if tab_id is not None:
            self._on_tab_changed(tab_id)
            return
        theme_mgr = self._container.theme_manager if self._container else None
        if theme_mgr and command_id == "theme_light":
            theme_mgr.set_theme(THEME_LIGHT)
        elif theme_mgr and command_id == "theme_dark":
            theme_mgr.set_theme(THEME_DARK)

    def _on_tab_changed(self, tab_id: str) -> None:
        self._stack_controller.switch_to(tab_id)
        self._sidebar.set_current_tab(tab_id)

    def _on_theme_changed(self, _name: str) -> None:
        w = self._stack.currentWidget()
        if w is not None and hasattr(w, "refresh_theme"):
            w.refresh_theme()

    def _restore_geometry(self) -> None:
        geom = self._settings.get_main_window_geometry()
        if isinstance(geom, QByteArray) and not geom.isEmpty():
            self.restoreGeometry(geom)
        state = self._settings.get_main_window_state()
        if isinstance(state, QByteArray) and not state.isEmpty():
            self.restoreState(state)

    def _save_geometry(self) -> None:
        self._settings.set_main_window_geometry(self.saveGeometry())
        self._settings.set_main_window_state(self.saveState())
        self._settings.set_sidebar_collapsed(self._sidebar.is_collapsed())
        self._settings.sync()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_geometry()
        super().closeEvent(event)
