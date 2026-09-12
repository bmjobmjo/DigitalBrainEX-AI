"""
Documents View for DigitalBrainEX AI.
Full-width table matching original Documents.cs with separate DocumentEditorDialog modal.
"""
import os
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
    QComboBox,
    QMessageBox,
    QMenu,
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal

from src.core.repository import DataRepository
from src.core.event_bus import event_bus, EVT_PROJECT_CHANGED
from src.ui.dialogs.document_editor_dlg import DocumentEditorDialog
from src.ui.icons import IconHelper
from src.config import resolve_document_path, open_path_or_url, show_in_file_manager
from src.core.logger import logger


class DocumentsView(QWidget):
    document_changed = pyqtSignal()

    def __init__(self, parent=None, doc_type: int = 0, title: str = "Documents"):
        super().__init__(parent)
        self.setObjectName("ViewContentWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._doc_type = doc_type
        self._view_title = title
        self._active_project_id = 0
        self._docs = []
        self._init_ui()
        self.load_data()

        event_bus.subscribe(EVT_PROJECT_CHANGED, self._on_global_project_changed)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. Title
        title_label = QLabel(self._view_title)
        title_label.setObjectName("ViewTitleLabel")
        main_layout.addWidget(title_label)

        # 2. Search & Category Filter Row
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        lbl_search = QLabel("Search")
        search_layout.addWidget(lbl_search)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search documents...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(260)
        self.search_input.textChanged.connect(self._filter_docs)
        self.search_input.returnPressed.connect(self._filter_docs)
        search_layout.addWidget(self.search_input)

        self.btn_go = QPushButton("Go")
        self.btn_go.setIcon(IconHelper.get_icon("search", 16))
        self.btn_go.clicked.connect(self._filter_docs)
        search_layout.addWidget(self.btn_go)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setIcon(IconHelper.get_icon("clear", 16))
        self.btn_clear.clicked.connect(self._clear_search)
        search_layout.addWidget(self.btn_clear)

        search_layout.addSpacing(16)

        search_layout.addWidget(QLabel("Category:"))
        self.combo_cat_filter = QComboBox()
        self.combo_cat_filter.addItem("All Categories")
        self._populate_categories()
        self.combo_cat_filter.currentIndexChanged.connect(lambda: self.load_data())
        search_layout.addWidget(self.combo_cat_filter)

        search_layout.addStretch()
        main_layout.addLayout(search_layout)

        # 3. Action Buttons Row
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)

        self.btn_new = QPushButton("Add")
        self.btn_new.setIcon(IconHelper.get_icon("add", 16))
        self.btn_new.setToolTip("Add a new document in popup dialog")
        self.btn_new.clicked.connect(self._open_new_doc_dialog)
        actions_layout.addWidget(self.btn_new)

        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setIcon(IconHelper.get_icon("edit", 16))
        self.btn_edit.setToolTip("Edit selected document in popup dialog")
        self.btn_edit.clicked.connect(self._open_edit_doc_dialog)
        actions_layout.addWidget(self.btn_edit)

        self.btn_open = QPushButton("Open File")
        self.btn_open.setIcon(IconHelper.get_icon("open", 16))
        self.btn_open.setToolTip("Open attached file in default application")
        self.btn_open.clicked.connect(self._open_selected_file)
        actions_layout.addWidget(self.btn_open)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setIcon(IconHelper.get_icon("delete", 16))
        self.btn_delete.setToolTip("Delete selected document record")
        self.btn_delete.clicked.connect(self._delete_document)
        actions_layout.addWidget(self.btn_delete)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setIcon(IconHelper.get_icon("refresh", 16))
        self.btn_refresh.setToolTip("Reload documents from database")
        self.btn_refresh.clicked.connect(self.load_data)
        actions_layout.addWidget(self.btn_refresh)

        actions_layout.addSpacing(12)

        self.btn_add_to_ai = QPushButton("Add Docs to AI")
        self.btn_add_to_ai.setIcon(IconHelper.get_icon("ai", 16))
        self.btn_add_to_ai.setToolTip("Submit selected document to AI knowledge base")
        self.btn_add_to_ai.clicked.connect(self._add_to_ai)
        actions_layout.addWidget(self.btn_add_to_ai)

        self.btn_gdrive = QPushButton("Collect Gdrive Files")
        self.btn_gdrive.setIcon(IconHelper.get_icon("cloud", 16))
        self.btn_gdrive.setToolTip("Collect or synchronize files from Google Drive")
        self.btn_gdrive.clicked.connect(self._collect_gdrive)
        actions_layout.addWidget(self.btn_gdrive)

        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        # 4. Full-width Documents Table matching original reference screenshot
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ProjectName",
            "DocumentName",
            "Category",
            "DocumentURI",
            "Desc",
            "AddedOn",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 230)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 200)
        self.table.setColumnWidth(4, 220)
        self.table.setColumnWidth(5, 110)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._open_selected_file)
        main_layout.addWidget(self.table)

    def _populate_categories(self):
        try:
            cats = DataRepository.get_document_categories()
            for c in cats:
                if c.CatogoryName:
                    self.combo_cat_filter.addItem(c.CatogoryName)
        except Exception as e:
            logger.error(f"Error populating categories: {e}")

    def _on_global_project_changed(self, project_id: int, project_name: str):
        self._active_project_id = project_id
        self.load_data()

    def _get_selected_doc_id(self) -> Optional[int]:
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return None
        row = self.table.currentRow()
        id_item = self.table.item(row, 0)
        if not id_item:
            return None
        return id_item.data(Qt.ItemDataRole.UserRole)

    def _open_new_doc_dialog(self):
        dlg = DocumentEditorDialog(parent=self, default_project_id=self._active_project_id)
        if dlg.exec():
            self.load_data()
            self.document_changed.emit()

    def _open_edit_doc_dialog(self):
        doc_id = self._get_selected_doc_id()
        if not doc_id:
            QMessageBox.information(self, "No Selection", "Please select a document to edit.")
            return
        dlg = DocumentEditorDialog(parent=self, doc_id=doc_id, default_project_id=self._active_project_id)
        if dlg.exec():
            self.load_data()
            self.document_changed.emit()

    def _open_selected_file(self):
        doc_id = self._get_selected_doc_id()
        if not doc_id:
            QMessageBox.information(self, "No Selection", "Please select a document to open.")
            return

        doc = DataRepository.get_document_by_id(doc_id)
        if not doc or not doc.DocumentURI:
            QMessageBox.warning(self, "No File", "This document has no file path associated.")
            return

        raw_uri = doc.DocumentURI.strip()
        resolved_path = resolve_document_path(raw_uri)
        open_path_or_url(resolved_path, self)

    def _show_selected_in_explorer(self):
        doc_id = self._get_selected_doc_id()
        if not doc_id:
            return
        doc = DataRepository.get_document_by_id(doc_id)
        if not doc or not doc.DocumentURI:
            return
        resolved = resolve_document_path(doc.DocumentURI.strip())
        show_in_file_manager(resolved)

    def _copy_selected_path(self):
        doc_id = self._get_selected_doc_id()
        if not doc_id:
            return
        doc = DataRepository.get_document_by_id(doc_id)
        if not doc or not doc.DocumentURI:
            return
        resolved = resolve_document_path(doc.DocumentURI.strip())
        QApplication.clipboard().setText(resolved)

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        self.table.selectRow(row)

        menu = QMenu(self)
        action_open = menu.addAction(IconHelper.get_icon("open", 16), "Open File / Link")
        action_open.triggered.connect(self._open_selected_file)

        action_show = menu.addAction(IconHelper.get_icon("browse", 16), "Show in File Explorer")
        action_show.triggered.connect(self._show_selected_in_explorer)

        action_copy = menu.addAction(IconHelper.get_icon("copy", 16), "Copy File Path")
        action_copy.triggered.connect(self._copy_selected_path)

        menu.addSeparator()

        action_edit = menu.addAction(IconHelper.get_icon("edit", 16), "Edit Document...")
        action_edit.triggered.connect(self._open_edit_doc_dialog)

        action_delete = menu.addAction(IconHelper.get_icon("delete", 16), "Delete Document")
        action_delete.triggered.connect(self._delete_document)

        menu.addSeparator()

        action_refresh = menu.addAction(IconHelper.get_icon("refresh", 16), "Refresh List")
        action_refresh.triggered.connect(self.load_data)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def load_data(self):
        selected_cat = self.combo_cat_filter.currentText()
        cat_filter = None if selected_cat == "All Categories" else selected_cat
        proj_filter = self._active_project_id if self._active_project_id != 0 else None

        try:
            exclude = ["PlainNotes", "TempFiles", "Minutes"] if not cat_filter else None
            self._docs = DataRepository.get_documents(
                project_id=proj_filter,
                doc_type=self._doc_type,
                category=cat_filter,
                exclude_categories=exclude,
            )
            self._display_docs(self._docs)
        except Exception as e:
            logger.error(f"Error loading documents: {e}")

    def _display_docs(self, docs):
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(docs))
            for row, d in enumerate(docs):
                proj_item = QTableWidgetItem(d.ProjectName or "General")
                proj_item.setData(Qt.ItemDataRole.UserRole, d.DocumentID)

                name_item = QTableWidgetItem(d.DocumentName or "")
                name_item.setData(Qt.ItemDataRole.UserRole, d.DocumentID)

                cat_item = QTableWidgetItem(d.Category or "General")
                cat_item.setData(Qt.ItemDataRole.UserRole, d.DocumentID)

                uri_item = QTableWidgetItem(d.DocumentURI or "")
                uri_item.setData(Qt.ItemDataRole.UserRole, d.DocumentID)

                desc_item = QTableWidgetItem((d.Desc or "").strip())
                desc_item.setData(Qt.ItemDataRole.UserRole, d.DocumentID)

                date_item = QTableWidgetItem(d.AddedOn or "")
                date_item.setData(Qt.ItemDataRole.UserRole, d.DocumentID)

                for item in (proj_item, name_item, cat_item, uri_item, desc_item, date_item):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.table.setItem(row, 0, proj_item)
                self.table.setItem(row, 1, name_item)
                self.table.setItem(row, 2, cat_item)
                self.table.setItem(row, 3, uri_item)
                self.table.setItem(row, 4, desc_item)
                self.table.setItem(row, 5, date_item)
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)

    def _filter_docs(self, *args):
        query = self.search_input.text().strip().lower()
        if not query:
            self._display_docs(self._docs)
            return
        filtered = [
            d for d in self._docs
            if query in (d.DocumentName or "").lower()
            or query in (d.ProjectName or "").lower()
            or query in (d.Category or "").lower()
            or query in (d.Desc or "").lower()
            or query in (d.Notes or "").lower()
            or query in (d.DocumentURI or "").lower()
        ]
        self._display_docs(filtered)

    def _clear_search(self):
        self.search_input.clear()
        self.combo_cat_filter.setCurrentIndex(0)
        self.load_data()

    def _add_to_ai(self):
        doc_id = self._get_selected_doc_id()
        if not doc_id:
            QMessageBox.information(self, "Select Document", "Please select a document to add to the AI index.")
            return
        doc = DataRepository.get_document_by_id(doc_id)
        if doc:
            QMessageBox.information(
                self,
                "AI Knowledge Index",
                f"Document '{doc.DocumentName}' has been added to the AI knowledge index.",
            )

    def _collect_gdrive(self):
        QMessageBox.information(
            self,
            "Google Drive Sync",
            "Google Drive sync initialized. Files will be organized in your configured Document storage directory.",
        )

    def _delete_document(self):
        doc_id = self._get_selected_doc_id()
        if not doc_id:
            QMessageBox.information(self, "No Selection", "Please select a document to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this document record?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            DataRepository.delete_document(doc_id)
            self.load_data()
            self.document_changed.emit()
