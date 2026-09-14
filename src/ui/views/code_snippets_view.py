"""
Code Snippets View for DigitalBrainEX AI.
Full-width table matching original CodeSnippets.cs with separate CodeSnippetEditorDialog modal.
"""
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QMenu,
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal

from src.core.repository import DataRepository
from src.core.event_bus import event_bus, EVT_PROJECT_CHANGED
from src.ui.dialogs.code_snippet_editor_dlg import CodeSnippetEditorDialog
from src.ui.icons import IconHelper
from src.core.logger import logger


class CodeSnippetsView(QWidget):
    snippet_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewContentWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._active_project_id = 0
        self._snippets = []
        self._init_ui()
        self.load_data()

        event_bus.subscribe(EVT_PROJECT_CHANGED, self._on_global_project_changed)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. Title
        title_label = QLabel("Code Snippets")
        title_label.setObjectName("ViewTitleLabel")
        main_layout.addWidget(title_label)

        # 2. Search Row
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        lbl_search = QLabel("Search")
        search_layout.addWidget(lbl_search)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search snippets...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._filter_snippets)
        self.search_input.returnPressed.connect(self._filter_snippets)
        search_layout.addWidget(self.search_input)

        self.btn_go = QPushButton("Go")
        self.btn_go.setIcon(IconHelper.get_icon("search", 16))
        self.btn_go.clicked.connect(self._filter_snippets)
        search_layout.addWidget(self.btn_go)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setIcon(IconHelper.get_icon("clear", 16))
        self.btn_clear.clicked.connect(self._clear_search)
        search_layout.addWidget(self.btn_clear)

        search_layout.addStretch()
        main_layout.addLayout(search_layout)

        # 3. Action Buttons Row
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)

        self.btn_new = QPushButton("Add")
        self.btn_new.setIcon(IconHelper.get_icon("add", 16))
        self.btn_new.setToolTip("Create a new code snippet in popup dialog")
        self.btn_new.clicked.connect(self._open_new_snippet_dialog)
        actions_layout.addWidget(self.btn_new)

        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setIcon(IconHelper.get_icon("edit", 16))
        self.btn_edit.setToolTip("Edit selected code snippet in popup dialog")
        self.btn_edit.clicked.connect(self._open_edit_snippet_dialog)
        actions_layout.addWidget(self.btn_edit)

        self.btn_copy_code = QPushButton("Copy Code")
        self.btn_copy_code.setIcon(IconHelper.get_icon("copy", 16))
        self.btn_copy_code.setToolTip("Copy code of selected snippet to clipboard")
        self.btn_copy_code.clicked.connect(self._copy_selected_code)
        actions_layout.addWidget(self.btn_copy_code)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setIcon(IconHelper.get_icon("delete", 16))
        self.btn_delete.setToolTip("Delete selected code snippet")
        self.btn_delete.clicked.connect(self._delete_snippet)
        actions_layout.addWidget(self.btn_delete)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setIcon(IconHelper.get_icon("refresh", 16))
        self.btn_refresh.setToolTip("Reload snippets from database")
        self.btn_refresh.clicked.connect(self.load_data)
        actions_layout.addWidget(self.btn_refresh)

        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        # 4. Full-width Snippets Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Language", "Project", "Date Added"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 65)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(3, 160)
        self.table.setColumnWidth(4, 130)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._open_edit_snippet_dialog)
        main_layout.addWidget(self.table)

    def _on_global_project_changed(self, project_id: int, project_name: str):
        self._active_project_id = project_id
        self.load_data()

    def _get_selected_snippet_id(self) -> Optional[int]:
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return None
        row = self.table.currentRow()
        id_item = self.table.item(row, 0)
        if not id_item:
            return None
        return id_item.data(Qt.ItemDataRole.UserRole)

    def _open_new_snippet_dialog(self):
        dlg = CodeSnippetEditorDialog(parent=self, default_project_id=self._active_project_id)
        if dlg.exec():
            self.load_data()
            self.snippet_changed.emit()

    def _open_edit_snippet_dialog(self, *args):
        if args and hasattr(args[0], "row"):
            self.table.selectRow(args[0].row())
        snippet_id = self._get_selected_snippet_id()
        if not snippet_id:
            QMessageBox.information(self, "No Selection", "Please select a code snippet to edit.")
            return
        dlg = CodeSnippetEditorDialog(parent=self, snippet_id=snippet_id, default_project_id=self._active_project_id)
        if dlg.exec():
            self.load_data()
            self.snippet_changed.emit()

    def _copy_selected_code(self):
        snippet_id = self._get_selected_snippet_id()
        if not snippet_id:
            QMessageBox.information(self, "No Selection", "Please select a snippet to copy.")
            return
        doc = DataRepository.get_document_by_id(snippet_id)
        if doc:
            code = doc.Notes or doc.Desc or ""
            if code:
                QApplication.clipboard().setText(code)
                QMessageBox.information(self, "Copied", "Code snippet copied to clipboard!")
            else:
                QMessageBox.warning(self, "Empty Snippet", "This snippet contains no code.")

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        self.table.selectRow(row)

        menu = QMenu(self)
        action_copy = menu.addAction(IconHelper.get_icon("copy", 16), "Copy Code to Clipboard")
        action_copy.triggered.connect(self._copy_selected_code)

        menu.addSeparator()

        action_edit = menu.addAction(IconHelper.get_icon("edit", 16), "Edit Snippet...")
        action_edit.triggered.connect(self._open_edit_snippet_dialog)

        action_delete = menu.addAction(IconHelper.get_icon("delete", 16), "Delete Snippet")
        action_delete.triggered.connect(self._delete_snippet)

        menu.addSeparator()

        action_refresh = menu.addAction(IconHelper.get_icon("refresh", 16), "Refresh List")
        action_refresh.triggered.connect(self.load_data)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def load_data(self):
        proj_filter = self._active_project_id if self._active_project_id != 0 else None
        try:
            self._snippets = DataRepository.get_code_snippets(project_id=proj_filter)
            self._display_snippets(self._snippets)
        except Exception as e:
            logger.error(f"Error loading code snippets: {e}")

    def _display_snippets(self, snippets):
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(snippets))
            for row, s in enumerate(snippets):
                id_item = QTableWidgetItem(str(s.DocumentID))
                id_item.setData(Qt.ItemDataRole.UserRole, s.DocumentID)
                title_item = QTableWidgetItem(s.DocumentName or "")
                lang_item = QTableWidgetItem(s.Language or "Code")
                proj_item = QTableWidgetItem(s.ProjectName or "General")
                date_item = QTableWidgetItem(s.AddedOn or "")

                for item in (id_item, title_item, lang_item, proj_item, date_item):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.table.setItem(row, 0, id_item)
                self.table.setItem(row, 1, title_item)
                self.table.setItem(row, 2, lang_item)
                self.table.setItem(row, 3, proj_item)
                self.table.setItem(row, 4, date_item)
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)

    def _filter_snippets(self, *args):
        query = self.search_input.text().strip().lower()
        if not query:
            self._display_snippets(self._snippets)
            return
        terms = [t.strip() for t in query.split("+") if t.strip()]
        filtered = [
            s for s in self._snippets
            if all(
                term in (s.DocumentName or "").lower()
                or term in (s.Desc or "").lower()
                or term in (s.Notes or "").lower()
                or term in (s.Language or "").lower()
                or term in (s.ProjectName or "").lower()
                for term in terms
            )
        ]
        self._display_snippets(filtered)

    def _clear_search(self):
        self.search_input.clear()
        self.load_data()

    def _delete_snippet(self):
        snippet_id = self._get_selected_snippet_id()
        if not snippet_id:
            QMessageBox.information(self, "No Selection", "Please select a code snippet to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this code snippet?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            DataRepository.delete_document(snippet_id)
            self.load_data()
            self.snippet_changed.emit()
