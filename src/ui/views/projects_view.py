"""
Projects View for DigitalBrainEX AI.
Full-width table matching original Projects.cs with separate ProjectEditorDialog modal.
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
)
from PyQt6.QtCore import Qt, pyqtSignal

from src.core.repository import DataRepository
from src.ui.dialogs.project_editor_dlg import ProjectEditorDialog
from src.ui.icons import IconHelper
from src.core.logger import logger


class ProjectsView(QWidget):
    project_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewContentWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._projects = []
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. Title
        title_label = QLabel("Projects")
        title_label.setObjectName("ViewTitleLabel")
        main_layout.addWidget(title_label)

        # 2. Search Row
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        lbl_search = QLabel("Search")
        search_layout.addWidget(lbl_search)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search projects...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._filter_projects)
        self.search_input.returnPressed.connect(self._filter_projects)
        search_layout.addWidget(self.search_input)

        self.btn_go = QPushButton("Go")
        self.btn_go.setIcon(IconHelper.get_icon("search", 16))
        self.btn_go.clicked.connect(self._filter_projects)
        search_layout.addWidget(self.btn_go)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setIcon(IconHelper.get_icon("clear", 16))
        self.btn_clear.clicked.connect(self._clear_search)
        search_layout.addWidget(self.btn_clear)

        search_layout.addStretch()
        main_layout.addLayout(search_layout)

        # 3. Action Buttons Row (Add, Edit, Delete, Refresh)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)

        self.btn_new = QPushButton("Add")
        self.btn_new.setIcon(IconHelper.get_icon("add", 16))
        self.btn_new.setToolTip("Create a new project in popup dialog")
        self.btn_new.clicked.connect(self._open_new_project_dialog)
        actions_layout.addWidget(self.btn_new)

        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setIcon(IconHelper.get_icon("edit", 16))
        self.btn_edit.setToolTip("Edit selected project in popup dialog")
        self.btn_edit.clicked.connect(self._open_edit_project_dialog)
        actions_layout.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setIcon(IconHelper.get_icon("delete", 16))
        self.btn_delete.setToolTip("Delete selected project")
        self.btn_delete.clicked.connect(self._delete_project)
        actions_layout.addWidget(self.btn_delete)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setIcon(IconHelper.get_icon("refresh", 16))
        self.btn_refresh.setToolTip("Reload projects from database")
        self.btn_refresh.clicked.connect(self.load_data)
        actions_layout.addWidget(self.btn_refresh)

        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        # 4. Full-width Projects Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ProjectName", "Desc", "Notes", "StartDate", "Status", "ID"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(1, 280)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 140)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 60)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._open_edit_project_dialog)
        main_layout.addWidget(self.table)

    def _get_selected_project_id(self) -> Optional[int]:
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return None
        row = self.table.currentRow()
        id_item = self.table.item(row, 0)
        if not id_item:
            return None
        return id_item.data(Qt.ItemDataRole.UserRole)

    def _open_new_project_dialog(self):
        dlg = ProjectEditorDialog(parent=self)
        if dlg.exec():
            self.load_data()
            self.project_updated.emit()

    def _open_edit_project_dialog(self):
        project_id = self._get_selected_project_id()
        if not project_id:
            QMessageBox.information(self, "No Selection", "Please select a project to edit.")
            return
        dlg = ProjectEditorDialog(parent=self, project_id=project_id)
        if dlg.exec():
            self.load_data()
            self.project_updated.emit()

    def load_data(self):
        """Loads projects from the database into table."""
        try:
            self._projects = DataRepository.get_all_projects()
            self._display_projects(self._projects)
        except Exception as e:
            logger.error(f"Error loading projects: {e}")

    def _display_projects(self, projects):
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(projects))
            for row, p in enumerate(projects):
                name_item = QTableWidgetItem(p.ProjectName or "")
                name_item.setData(Qt.ItemDataRole.UserRole, p.PojectID)
                desc_item = QTableWidgetItem((p.Desc or "").strip())
                notes_item = QTableWidgetItem((p.Notes or "").strip())
                date_item = QTableWidgetItem(p.StartDate or "")
                status_item = QTableWidgetItem(p.Status or "Active")
                id_item = QTableWidgetItem(str(p.PojectID))

                for item in (name_item, desc_item, notes_item, date_item, status_item, id_item):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.table.setItem(row, 0, name_item)
                self.table.setItem(row, 1, desc_item)
                self.table.setItem(row, 2, notes_item)
                self.table.setItem(row, 3, date_item)
                self.table.setItem(row, 4, status_item)
                self.table.setItem(row, 5, id_item)
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)

    def _filter_projects(self, *args):
        query = self.search_input.text().strip().lower()
        if not query:
            self._display_projects(self._projects)
            return
        filtered = [
            p for p in self._projects
            if query in (p.ProjectName or "").lower()
            or query in (p.Desc or "").lower()
            or query in (p.Notes or "").lower()
        ]
        self._display_projects(filtered)

    def _clear_search(self):
        self.search_input.clear()
        self.load_data()

    def _delete_project(self):
        project_id = self._get_selected_project_id()
        if not project_id:
            QMessageBox.information(self, "No Selection", "Please select a project to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this project?\nAssociated items may lose project link.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            DataRepository.delete_project(project_id)
            self.load_data()
            self.project_updated.emit()

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        self.table.selectRow(row)

        menu = QMenu(self)
        action_edit = menu.addAction(IconHelper.get_icon("edit", 16), "Edit Project...")
        action_edit.triggered.connect(self._open_edit_project_dialog)

        action_delete = menu.addAction(IconHelper.get_icon("delete", 16), "Delete Project")
        action_delete.triggered.connect(self._delete_project)

        menu.addSeparator()

        action_refresh = menu.addAction(IconHelper.get_icon("refresh", 16), "Refresh List")
        action_refresh.triggered.connect(self.load_data)

        menu.exec(self.table.viewport().mapToGlobal(pos))
