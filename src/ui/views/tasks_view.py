"""
Tasks & Reminders View for DigitalBrainEX AI.
Full-width table with top action toolbar and separate TaskEditorDialog modal.
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
    QComboBox,
    QMessageBox,
    QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal

from src.core.repository import DataRepository
from src.core.event_bus import event_bus, EVT_PROJECT_CHANGED
from src.ui.dialogs.task_editor_dlg import TaskEditorDialog
from src.ui.icons import IconHelper
from src.core.logger import logger


class TasksView(QWidget):
    task_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewContentWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._active_project_id = 0
        self._all_tasks = []
        self._init_ui()
        self.load_data()

        # Subscribe to global project changes
        event_bus.subscribe(EVT_PROJECT_CHANGED, self._on_global_project_changed)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. Title
        title_label = QLabel("Tasks & Reminders")
        title_label.setObjectName("ViewTitleLabel")
        main_layout.addWidget(title_label)

        # 2. Search & Filter Row
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        lbl_search = QLabel("Search")
        search_layout.addWidget(lbl_search)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tasks...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(260)
        self.search_input.textChanged.connect(self._filter_tasks)
        self.search_input.returnPressed.connect(self._filter_tasks)
        search_layout.addWidget(self.search_input)

        self.btn_go = QPushButton("Go")
        self.btn_go.setIcon(IconHelper.get_icon("search", 16))
        self.btn_go.clicked.connect(self._filter_tasks)
        search_layout.addWidget(self.btn_go)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setIcon(IconHelper.get_icon("clear", 16))
        self.btn_clear.clicked.connect(self._clear_search)
        search_layout.addWidget(self.btn_clear)

        search_layout.addSpacing(16)

        search_layout.addWidget(QLabel("Filter:"))
        self.combo_filter = QComboBox()
        self.combo_filter.addItems(["Active Tasks", "Today's Tasks", "Closed Tasks", "All Tasks"])
        self.combo_filter.setFixedWidth(130)
        self.combo_filter.currentIndexChanged.connect(lambda: self.load_data())
        search_layout.addWidget(self.combo_filter)

        search_layout.addStretch()
        main_layout.addLayout(search_layout)

        # 3. Action Buttons Row (New Task, Edit, Complete, Delete, Refresh)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)

        self.btn_new = QPushButton("New Task")
        self.btn_new.setIcon(IconHelper.get_icon("add", 16))
        self.btn_new.setToolTip("Create a new task in popup dialog")
        self.btn_new.clicked.connect(self._open_new_task_dialog)
        actions_layout.addWidget(self.btn_new)

        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setIcon(IconHelper.get_icon("edit", 16))
        self.btn_edit.setToolTip("Edit selected task in popup dialog")
        self.btn_edit.clicked.connect(self._open_edit_task_dialog)
        actions_layout.addWidget(self.btn_edit)

        self.btn_complete = QPushButton("Complete")
        self.btn_complete.setIcon(IconHelper.get_icon("complete", 16))
        self.btn_complete.setToolTip("Toggle completion status of selected task")
        self.btn_complete.clicked.connect(self._toggle_complete)
        actions_layout.addWidget(self.btn_complete)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setIcon(IconHelper.get_icon("delete", 16))
        self.btn_delete.setToolTip("Delete selected task")
        self.btn_delete.clicked.connect(self._delete_task)
        actions_layout.addWidget(self.btn_delete)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setIcon(IconHelper.get_icon("refresh", 16))
        self.btn_refresh.setToolTip("Reload tasks from database")
        self.btn_refresh.clicked.connect(self.load_data)
        actions_layout.addWidget(self.btn_refresh)

        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        # 4. Full-width Tasks Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Task Name", "Due Date", "Project", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 65)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 160)
        self.table.setColumnWidth(4, 95)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._open_edit_task_dialog)
        main_layout.addWidget(self.table)

    def _on_global_project_changed(self, project_id: int, project_name: str):
        self._active_project_id = project_id
        self.load_data()

    def _get_selected_task_id(self) -> Optional[int]:
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return None
        row = self.table.currentRow()
        id_item = self.table.item(row, 0)
        if not id_item:
            return None
        return id_item.data(Qt.ItemDataRole.UserRole)

    def _open_new_task_dialog(self):
        dlg = TaskEditorDialog(parent=self, default_project_id=self._active_project_id)
        if dlg.exec():
            self.load_data()
            self.task_changed.emit()

    def _open_edit_task_dialog(self):
        task_id = self._get_selected_task_id()
        if not task_id:
            QMessageBox.information(self, "No Selection", "Please select a task to edit.")
            return
        dlg = TaskEditorDialog(parent=self, task_id=task_id, default_project_id=self._active_project_id)
        if dlg.exec():
            self.load_data()
            self.task_changed.emit()

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        self.table.selectRow(row)

        menu = QMenu(self)
        action_edit = menu.addAction(IconHelper.get_icon("edit", 16), "Edit Task...")
        action_edit.triggered.connect(self._open_edit_task_dialog)

        action_complete = menu.addAction(IconHelper.get_icon("complete", 16), "Toggle Complete")
        action_complete.triggered.connect(self._toggle_complete)

        action_delete = menu.addAction(IconHelper.get_icon("delete", 16), "Delete Task")
        action_delete.triggered.connect(self._delete_task)

        menu.addSeparator()

        action_refresh = menu.addAction(IconHelper.get_icon("refresh", 16), "Refresh List")
        action_refresh.triggered.connect(self.load_data)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def load_data(self):
        """Loads tasks according to selected filter."""
        filter_text = self.combo_filter.currentText()
        proj_filter = str(self._active_project_id) if self._active_project_id != 0 else None

        try:
            if "Today" in filter_text:
                self._all_tasks = DataRepository.get_todays_tasks(project_id=proj_filter)
            elif "Closed" in filter_text:
                self._all_tasks = DataRepository.get_tasks(project_id=proj_filter, status="Closed")
            elif "All" in filter_text:
                self._all_tasks = DataRepository.get_tasks(project_id=proj_filter, status="All")
            else:
                self._all_tasks = DataRepository.get_tasks(project_id=proj_filter, status="Active")

            self._display_tasks(self._all_tasks)
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")

    def _display_tasks(self, tasks):
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(tasks))
            for row, t in enumerate(tasks):
                id_item = QTableWidgetItem(str(t.TaskID))
                id_item.setData(Qt.ItemDataRole.UserRole, t.TaskID)
                name_item = QTableWidgetItem(t.TaskName or "")
                due_item = QTableWidgetItem(t.DueOn or "")
                proj_item = QTableWidgetItem(t.ProjectName or "General")
                status_item = QTableWidgetItem(t.Status or "Active")

                for item in (id_item, name_item, due_item, proj_item, status_item):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.table.setItem(row, 0, id_item)
                self.table.setItem(row, 1, name_item)
                self.table.setItem(row, 2, due_item)
                self.table.setItem(row, 3, proj_item)
                self.table.setItem(row, 4, status_item)
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)

    def _filter_tasks(self, *args):
        query = self.search_input.text().strip().lower()
        if not query:
            self._display_tasks(self._all_tasks)
            return
        filtered = [
            t for t in self._all_tasks
            if query in (t.TaskName or "").lower() or query in (t.TaskDesc or "").lower()
        ]
        self._display_tasks(filtered)

    def _clear_search(self):
        self.search_input.clear()
        self.combo_filter.setCurrentIndex(0)
        self.load_data()

    def _toggle_complete(self):
        task_id = self._get_selected_task_id()
        if not task_id:
            QMessageBox.information(self, "No Selection", "Please select a task to toggle completion.")
            return

        tasks = [t for t in self._all_tasks if t.TaskID == task_id]
        if not tasks:
            return

        current_status = tasks[0].Status or "Active"
        new_status = "Closed" if current_status == "Active" else "Active"
        DataRepository.update_task(task_id, Status=new_status)
        self.load_data()
        self.task_changed.emit()

    def _delete_task(self):
        task_id = self._get_selected_task_id()
        if not task_id:
            QMessageBox.information(self, "No Selection", "Please select a task to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this task?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            DataRepository.delete_task(task_id)
            self.load_data()
            self.task_changed.emit()
