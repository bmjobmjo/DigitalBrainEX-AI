"""
URLs & Web Links View for DigitalBrainEX AI.
Full-width table matching original URLs.cs with separate UrlEditorDialog modal.
"""
import webbrowser
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
from src.ui.dialogs.url_editor_dlg import UrlEditorDialog
from src.ui.icons import IconHelper
from src.core.logger import logger


class UrlsView(QWidget):
    url_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewContentWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._active_project_id = 0
        self._urls = []
        self._init_ui()
        self.load_data()

        event_bus.subscribe(EVT_PROJECT_CHANGED, self._on_global_project_changed)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. Title
        title_label = QLabel("URLs & Bookmarks")
        title_label.setObjectName("ViewTitleLabel")
        main_layout.addWidget(title_label)

        # 2. Search Row
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        lbl_search = QLabel("Search")
        search_layout.addWidget(lbl_search)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search bookmarks...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._filter_urls)
        self.search_input.returnPressed.connect(self._filter_urls)
        search_layout.addWidget(self.search_input)

        self.btn_go = QPushButton("Go")
        self.btn_go.setIcon(IconHelper.get_icon("search", 16))
        self.btn_go.clicked.connect(self._filter_urls)
        search_layout.addWidget(self.btn_go)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setIcon(IconHelper.get_icon("clear", 16))
        self.btn_clear.clicked.connect(self._clear_search)
        search_layout.addWidget(self.btn_clear)

        search_layout.addStretch()
        main_layout.addLayout(search_layout)

        # 3. Actions Row
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)

        self.btn_new = QPushButton("Add")
        self.btn_new.setIcon(IconHelper.get_icon("add", 16))
        self.btn_new.setToolTip("Add a new bookmark in popup dialog")
        self.btn_new.clicked.connect(self._open_new_url_dialog)
        actions_layout.addWidget(self.btn_new)

        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setIcon(IconHelper.get_icon("edit", 16))
        self.btn_edit.setToolTip("Edit selected bookmark in popup dialog")
        self.btn_edit.clicked.connect(self._open_edit_url_dialog)
        actions_layout.addWidget(self.btn_edit)

        self.btn_open_browser = QPushButton("Open Browser")
        self.btn_open_browser.setIcon(IconHelper.get_icon("urls", 16))
        self.btn_open_browser.setToolTip("Open selected URL in default web browser")
        self.btn_open_browser.clicked.connect(self._open_selected_url)
        actions_layout.addWidget(self.btn_open_browser)

        self.btn_copy_url = QPushButton("Copy URL")
        self.btn_copy_url.setIcon(IconHelper.get_icon("copy", 16))
        self.btn_copy_url.setToolTip("Copy selected URL to clipboard")
        self.btn_copy_url.clicked.connect(self._copy_selected_url)
        actions_layout.addWidget(self.btn_copy_url)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setIcon(IconHelper.get_icon("delete", 16))
        self.btn_delete.setToolTip("Delete selected bookmark")
        self.btn_delete.clicked.connect(self._delete_url)
        actions_layout.addWidget(self.btn_delete)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setIcon(IconHelper.get_icon("refresh", 16))
        self.btn_refresh.setToolTip("Reload bookmarks from database")
        self.btn_refresh.clicked.connect(self.load_data)
        actions_layout.addWidget(self.btn_refresh)

        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        # 4. Full-width URLs Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Bookmark Name", "Web URL", "Project", "Category"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 65)
        self.table.setColumnWidth(1, 220)
        self.table.setColumnWidth(3, 150)
        self.table.setColumnWidth(4, 120)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._open_selected_url)
        main_layout.addWidget(self.table)

    def _on_global_project_changed(self, project_id: int, project_name: str):
        self._active_project_id = project_id
        self.load_data()

    def _get_selected_url_id(self) -> Optional[int]:
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return None
        row = self.table.currentRow()
        id_item = self.table.item(row, 0)
        if not id_item:
            return None
        return id_item.data(Qt.ItemDataRole.UserRole)

    def _open_new_url_dialog(self):
        dlg = UrlEditorDialog(parent=self, default_project_id=self._active_project_id)
        if dlg.exec():
            self.load_data()
            self.url_changed.emit()

    def _open_edit_url_dialog(self):
        url_id = self._get_selected_url_id()
        if not url_id:
            QMessageBox.information(self, "No Selection", "Please select a bookmark to edit.")
            return
        dlg = UrlEditorDialog(parent=self, url_id=url_id, default_project_id=self._active_project_id)
        if dlg.exec():
            self.load_data()
            self.url_changed.emit()

    def _open_selected_url(self):
        url_id = self._get_selected_url_id()
        if not url_id:
            QMessageBox.information(self, "No Selection", "Please select a bookmark to open.")
            return
        matches = [u for u in self._urls if u.UrlID == url_id]
        if matches and matches[0].Url:
            url = matches[0].Url.strip()
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            webbrowser.open(url)

    def _copy_selected_url(self):
        url_id = self._get_selected_url_id()
        if not url_id:
            QMessageBox.information(self, "No Selection", "Please select a bookmark to copy.")
            return
        matches = [u for u in self._urls if u.UrlID == url_id]
        if matches and matches[0].Url:
            QApplication.clipboard().setText(matches[0].Url.strip())
            QMessageBox.information(self, "Copied", "Bookmark URL copied to clipboard!")

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        self.table.selectRow(row)

        menu = QMenu(self)
        action_open = menu.addAction(IconHelper.get_icon("urls", 16), "Open in Web Browser")
        action_open.triggered.connect(self._open_selected_url)

        action_copy = menu.addAction(IconHelper.get_icon("copy", 16), "Copy URL")
        action_copy.triggered.connect(self._copy_selected_url)

        menu.addSeparator()

        action_edit = menu.addAction(IconHelper.get_icon("edit", 16), "Edit Bookmark...")
        action_edit.triggered.connect(self._open_edit_url_dialog)

        action_delete = menu.addAction(IconHelper.get_icon("delete", 16), "Delete Bookmark")
        action_delete.triggered.connect(self._delete_url)

        menu.addSeparator()

        action_refresh = menu.addAction(IconHelper.get_icon("refresh", 16), "Refresh List")
        action_refresh.triggered.connect(self.load_data)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def load_data(self):
        proj_filter = self._active_project_id if self._active_project_id != 0 else None
        try:
            self._urls = DataRepository.get_urls(project_id=proj_filter)
            self._display_urls(self._urls)
        except Exception as e:
            logger.error(f"Error loading URLs: {e}")

    def _display_urls(self, urls):
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(urls))
            for row, u in enumerate(urls):
                id_item = QTableWidgetItem(str(u.UrlID))
                id_item.setData(Qt.ItemDataRole.UserRole, u.UrlID)
                name_item = QTableWidgetItem(u.UrlName or "")
                url_item = QTableWidgetItem(u.Url or "")
                proj_item = QTableWidgetItem(u.ProjectName or "General")
                cat_item = QTableWidgetItem(u.Category or "General")

                for item in (id_item, name_item, url_item, proj_item, cat_item):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.table.setItem(row, 0, id_item)
                self.table.setItem(row, 1, name_item)
                self.table.setItem(row, 2, url_item)
                self.table.setItem(row, 3, proj_item)
                self.table.setItem(row, 4, cat_item)
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)

    def _filter_urls(self, *args):
        query = self.search_input.text().strip().lower()
        if not query:
            self._display_urls(self._urls)
            return
        filtered = [
            u for u in self._urls
            if query in (u.UrlName or "").lower()
            or query in (u.Url or "").lower()
            or query in (u.Notes or "").lower()
        ]
        self._display_docs(filtered) if hasattr(self, "_display_docs") else self._display_urls(filtered)

    def _clear_search(self):
        self.search_input.clear()
        self.load_data()

    def _delete_url(self):
        url_id = self._get_selected_url_id()
        if not url_id:
            QMessageBox.information(self, "No Selection", "Please select a bookmark to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this bookmark?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            DataRepository.delete_url(url_id)
            self.load_data()
            self.url_changed.emit()
