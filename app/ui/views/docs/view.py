from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QKeySequence, QShortcut, QTextDocument
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.application.docs_service import DocsService
from app.ui.viewmodels.docs_vm import DocsViewModel

log = logging.getLogger(__name__)


class DocsView(QWidget):
    def __init__(self, container, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._vm = DocsViewModel(DocsService(container.project_root / "docs"))
        self._current_rel_path: str | None = None
        self._build_ui()
        self._refresh_tree()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)

        left_panel = QWidget(self)
        left_layout = QVBoxLayout(left_panel)
        self._name_filter = QLineEdit(self)
        self._name_filter.setPlaceholderText("Фильтр по имени файла…")
        self._name_filter.textChanged.connect(self._refresh_tree)
        left_layout.addWidget(self._name_filter)

        self._tree = QTreeWidget(self)
        self._tree.setHeaderLabel("docs/")
        self._tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        left_layout.addWidget(self._tree, 1)

        root.addWidget(left_panel, 1)

        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        find_row = QHBoxLayout()
        self._content_search = QLineEdit(self)
        self._content_search.setPlaceholderText("Поиск по содержимому (Ctrl+F)…")
        self._content_search.returnPressed.connect(self._find_next)
        self._find_next_btn = QPushButton("Найти далее", self)
        self._find_next_btn.clicked.connect(self._find_next)
        find_row.addWidget(self._content_search, 1)
        find_row.addWidget(self._find_next_btn)
        right_layout.addLayout(find_row)

        self._viewer = QTextBrowser(self)
        self._viewer.setOpenLinks(False)
        self._viewer.anchorClicked.connect(self._on_anchor_clicked)
        right_layout.addWidget(self._viewer, 1)
        root.addWidget(right_panel, 2)

        self._find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self._find_shortcut.activated.connect(self._focus_content_search)

    def _focus_content_search(self) -> None:
        self._content_search.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self._content_search.selectAll()

    def _refresh_tree(self) -> None:
        query = self._name_filter.text()
        docs = self._vm.filter_by_name(query)
        self._tree.clear()
        folder_nodes: dict[Path, QTreeWidgetItem] = {}

        for entry in docs:
            rel_path = Path(entry.relative_path)
            parent_item = self._tree.invisibleRootItem()
            current_path = Path()
            for part in rel_path.parts[:-1]:
                current_path /= part
                if current_path not in folder_nodes:
                    folder_item = QTreeWidgetItem([part])
                    parent_item.addChild(folder_item)
                    folder_nodes[current_path] = folder_item
                parent_item = folder_nodes[current_path]
            leaf = QTreeWidgetItem([rel_path.name])
            leaf.setData(0, Qt.ItemDataRole.UserRole, entry.relative_path)
            parent_item.addChild(leaf)

        self._tree.expandAll()

    def _on_tree_selection_changed(self) -> None:
        current = self._tree.currentItem()
        if current is None:
            return
        rel_path = current.data(0, Qt.ItemDataRole.UserRole)
        if not rel_path:
            return
        self._open_doc(rel_path)

    def _open_doc(self, rel_path: str) -> None:
        try:
            text = self._vm.read_doc(rel_path)
        except OSError as exc:
            log.exception("Failed to open doc %s", rel_path)
            self._viewer.setPlainText(f"Не удалось открыть файл: {rel_path}\n{exc}")
            return
        self._current_rel_path = rel_path
        if rel_path.lower().endswith(".md"):
            self._viewer.setMarkdown(text)
        else:
            self._viewer.setPlainText(text)

    def _find_next(self) -> None:
        query = self._content_search.text().strip()
        if not query:
            return
        if not self._viewer.find(query, QTextDocument.FindFlag()):
            cursor = self._viewer.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            self._viewer.setTextCursor(cursor)
            self._viewer.find(query, QTextDocument.FindFlag())

    def _on_anchor_clicked(self, url: QUrl) -> None:
        target = url.toString().split("#", 1)[0]
        if not target:
            return
        if self._current_rel_path:
            base = Path(self._current_rel_path).parent
        else:
            base = Path()
        resolved = (base / target).as_posix()
        self._open_doc(resolved)

    def shutdown(self) -> None:
        return
