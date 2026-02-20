"""
Collapsible sidebar: icon-based navigation, tooltips, smooth width animation.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# Sidebar width in expanded/collapsed state
SIDEBAR_WIDTH_EXPANDED = 220
SIDEBAR_WIDTH_COLLAPSED = 56
ANIMATION_DURATION_MS = 200

if TYPE_CHECKING:
    from app.ui.infrastructure.di import Container


class SidebarButton(QToolButton):
    """Single nav button: icon + optional text (hidden when collapsed)."""

    def __init__(
        self,
        parent: QWidget | None,
        tab_id: str,
        label: str,
        tooltip: str,
        icon_style: QStyle.StandardPixmap,
    ) -> None:
        super().__init__(parent)
        self._tab_id = tab_id
        self._label = label
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setIcon(self.style().standardIcon(icon_style))
        self.setText(label)
        self.setToolTip(tooltip)
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(40)

    @property
    def tab_id(self) -> str:
        return self._tab_id


class CollapsibleSidebar(QFrame):
    """Vertical sidebar with nav buttons and collapse toggle. Emits tab change and collapse state."""

    tab_changed = Signal(str)  # tab_id

    def __init__(
        self,
        parent: QWidget | None,
        initial_collapsed: bool = False,
        container: Container | None = None,
    ) -> None:
        super().__init__(parent)
        self._collapsed = initial_collapsed
        self._container = container
        self._buttons: list[SidebarButton] = []
        self._animation: QPropertyAnimation | None = None

        self.setObjectName("collapsibleSidebar")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumWidth(SIDEBAR_WIDTH_COLLAPSED)
        self.setMaximumWidth(SIDEBAR_WIDTH_EXPANDED)
        self._set_sidebar_width(SIDEBAR_WIDTH_COLLAPSED if initial_collapsed else SIDEBAR_WIDTH_EXPANDED)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 12, 4, 8)
        layout.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(2)

        nav_items = [
            ("datasets", "Датасеты", "Управление датасетами и подготовка к YOLO", QStyle.StandardPixmap.SP_DirIcon),
            ("training", "Обучение", "Обучение моделей YOLO", QStyle.StandardPixmap.SP_MediaPlay),
            ("detection", "Детекция", "Детекция в реальном времени", QStyle.StandardPixmap.SP_ComputerIcon),
            ("integrations", "Интеграции", "Интеграции и мониторинг", QStyle.StandardPixmap.SP_DriveNetIcon),
            ("jobs", "Задачи", "История фоновых задач, логи и повтор", QStyle.StandardPixmap.SP_FileDialogDetailedView),
        ]
        for tab_id, label, tooltip, pixmap in nav_items:
            btn = SidebarButton(self, tab_id, label, tooltip, pixmap)
            btn.clicked.connect(lambda checked=False, t=tab_id: self._on_nav_clicked(t))
            self._buttons.append(btn)
            scroll_layout.addWidget(btn)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Theme switcher (Part 4.11: theme from DI container, no global get_theme_manager)
        from app.ui.theme.manager import THEME_DARK, THEME_LIGHT
        theme_mgr = self._container.theme_manager if self._container else None
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["Тёмная", "Светлая"])
        self._theme_combo.setCurrentIndex(1 if (theme_mgr and theme_mgr.get_theme() == THEME_LIGHT) else 0)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self._theme_label = QLabel("Тема:")
        theme_row = QWidget()
        theme_row_layout = QVBoxLayout(theme_row)
        theme_row_layout.setContentsMargins(4, 4, 4, 4)
        theme_row_layout.setSpacing(4)
        theme_row_layout.addWidget(self._theme_label)
        theme_row_layout.addWidget(self._theme_combo)
        self._theme_widget = theme_row
        layout.addWidget(self._theme_widget)
        if theme_mgr:
            theme_mgr.theme_changed.connect(self._sync_theme_combo)

        if initial_collapsed:
            for btn in self._buttons:
                btn.setText("")
            self._theme_widget.hide()

        self._toggle_btn = QToolButton(self)
        self._toggle_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle_btn.setIcon(
            self.style().standardIcon(
                QStyle.StandardPixmap.SP_ArrowLeft if not initial_collapsed else QStyle.StandardPixmap.SP_ArrowRight
            )
        )
        self._toggle_btn.setText("Свернуть" if not initial_collapsed else "")
        self._toggle_btn.setToolTip("Свернуть панель" if not initial_collapsed else "Развернуть панель")
        self._toggle_btn.setMinimumHeight(36)
        self._toggle_btn.clicked.connect(self._toggle_collapsed)
        layout.addWidget(self._toggle_btn)

    def _set_sidebar_width(self, w: int) -> None:
        self.setMinimumWidth(w)
        self.setMaximumWidth(w)

    def _on_nav_clicked(self, tab_id: str) -> None:
        for btn in self._buttons:
            btn.setChecked(btn.tab_id == tab_id)
        self.tab_changed.emit(tab_id)

    def _toggle_collapsed(self) -> None:
        self.set_collapsed(not self._collapsed)

    def is_collapsed(self) -> bool:
        return self._collapsed

    def set_collapsed(self, collapsed: bool) -> None:
        if self._collapsed == collapsed:
            return
        self._collapsed = collapsed
        target = SIDEBAR_WIDTH_COLLAPSED if collapsed else SIDEBAR_WIDTH_EXPANDED
        current = self.width()

        if self._animation is not None and self._animation.state() == QPropertyAnimation.State.Running:
            self._animation.stop()

        self._animation = QPropertyAnimation(self, b"minimumWidth")
        self._animation.setDuration(ANIMATION_DURATION_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.setStartValue(current)
        self._animation.setEndValue(target)
        self._animation.finished.connect(self._on_animation_finished)
        self._animation.start()

        anim_max = QPropertyAnimation(self, b"maximumWidth")
        anim_max.setDuration(ANIMATION_DURATION_MS)
        anim_max.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim_max.setStartValue(current)
        anim_max.setEndValue(target)
        anim_max.start()

        self._update_toggle_button()

    def _on_animation_finished(self) -> None:
        self._set_sidebar_width(SIDEBAR_WIDTH_COLLAPSED if self._collapsed else SIDEBAR_WIDTH_EXPANDED)
        for btn in self._buttons:
            btn.setText(btn._label if not self._collapsed else "")
        self._theme_widget.setVisible(not self._collapsed)

    def _on_theme_changed(self, index: int) -> None:
        from app.ui.theme.manager import THEME_DARK, THEME_LIGHT
        theme_mgr = self._container.theme_manager if self._container else None
        if theme_mgr:
            theme_mgr.set_theme(THEME_LIGHT if index == 1 else THEME_DARK)

    def _sync_theme_combo(self, name: str) -> None:
        from app.ui.theme.manager import THEME_LIGHT
        self._theme_combo.blockSignals(True)
        self._theme_combo.setCurrentIndex(1 if name == THEME_LIGHT else 0)
        self._theme_combo.blockSignals(False)

    def _update_toggle_button(self) -> None:
        if self._collapsed:
            self._toggle_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
            self._toggle_btn.setText("")
            self._toggle_btn.setToolTip("Развернуть панель")
        else:
            self._toggle_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
            self._toggle_btn.setText("Свернуть")
            self._toggle_btn.setToolTip("Свернуть панель")

    def set_current_tab(self, tab_id: str) -> None:
        for btn in self._buttons:
            btn.setChecked(btn.tab_id == tab_id)