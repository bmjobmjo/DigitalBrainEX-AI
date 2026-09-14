"""
Notes Listing View for DigitalBrainEX AI.
Full-width table matching original Notes.cs with separate NoteEditorDialog modal.
"""
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
from src.core.event_bus import event_bus, EVT_PROJECT_CHANGED
from src.ui.dialogs.note_editor_dlg import NoteEditorDialog
from src.ui.icons import IconHelper
from src.core.logger import logger


class NotesView(QWidget):
    note_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewContentWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._active_project_id = 0
        self._notes = []
        self._init_ui()
        self.load_data()

        event_bus.subscribe(EVT_PROJECT_CHANGED, self._on_global_project_changed)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. Title
        title_label = QLabel("Personal Diary & Notes")
        title_label.setObjectName("ViewTitleLabel")
        main_layout.addWidget(title_label)

        # 2. Search Row
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        lbl_search = QLabel("Search")
        search_layout.addWidget(lbl_search)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search notes...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._filter_notes)
        self.search_input.returnPressed.connect(self._filter_notes)
        search_layout.addWidget(self.search_input)

        self.btn_go = QPushButton("Go")
        self.btn_go.setIcon(IconHelper.get_icon("search", 16))
        self.btn_go.clicked.connect(self._filter_notes)
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
        self.btn_new.setToolTip("Create a new note in popup dialog")
        self.btn_new.clicked.connect(self._open_new_note_dialog)
        actions_layout.addWidget(self.btn_new)

        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setIcon(IconHelper.get_icon("edit", 16))
        self.btn_edit.setToolTip("Edit selected note in popup dialog")
        self.btn_edit.clicked.connect(self._open_edit_note_dialog)
        actions_layout.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setIcon(IconHelper.get_icon("delete", 16))
        self.btn_delete.setToolTip("Delete selected note")
        self.btn_delete.clicked.connect(self._delete_note)
        actions_layout.addWidget(self.btn_delete)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setIcon(IconHelper.get_icon("refresh", 16))
        self.btn_refresh.setToolTip("Reload notes from database")
        self.btn_refresh.clicked.connect(self.load_data)
        actions_layout.addWidget(self.btn_refresh)

        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        # 4. Full-Width Notes Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Description", "Project", "Date"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 65)
        self.table.setColumnWidth(1, 220)
        self.table.setColumnWidth(2, 280)
        self.table.setColumnWidth(3, 140)
        self.table.setColumnWidth(4, 120)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._open_edit_note_dialog)
        main_layout.addWidget(self.table)

    def _on_global_project_changed(self, project_id: int, project_name: str):
        self._active_project_id = project_id
        self.load_data()

    def load_data(self):
        proj_filter = self._active_project_id if self._active_project_id != 0 else None
        try:
            self._notes = DataRepository.get_notes(project_id=proj_filter)
            self._display_notes(self._notes)
        except Exception as e:
            logger.error(f"Error loading notes: {e}")

    def _display_notes(self, notes):
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(notes))
            for row, n in enumerate(notes):
                id_item = QTableWidgetItem(str(n.DocumentID))
                id_item.setData(Qt.ItemDataRole.UserRole, n.DocumentID)

                title_item = QTableWidgetItem(n.DocumentName or "")
                title_item.setData(Qt.ItemDataRole.UserRole, n.DocumentID)

                desc_text = (n.Desc or n.Notes or "").strip()
                desc_item = QTableWidgetItem(desc_text)
                desc_item.setData(Qt.ItemDataRole.UserRole, n.DocumentID)

                proj_item = QTableWidgetItem(n.ProjectName or "General")
                proj_item.setData(Qt.ItemDataRole.UserRole, n.DocumentID)

                date_item = QTableWidgetItem(n.AddedOn or "")
                date_item.setData(Qt.ItemDataRole.UserRole, n.DocumentID)

                for item in (id_item, title_item, desc_item, proj_item, date_item):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.table.setItem(row, 0, id_item)
                self.table.setItem(row, 1, title_item)
                self.table.setItem(row, 2, desc_item)
                self.table.setItem(row, 3, proj_item)
                self.table.setItem(row, 4, date_item)
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)

    def _filter_notes(self, *args):
        query = self.search_input.text().strip().lower()
        if not query:
            self._display_notes(self._notes)
            return
        terms = [t.strip() for t in query.split("+") if t.strip()]
        filtered = [
            n for n in self._notes
            if all(
                term in (n.DocumentName or "").lower()
                or term in (n.Desc or "").lower()
                or term in (n.Notes or "").lower()
                or term in (n.ProjectName or "").lower()
                for term in terms
            )
        ]
        self._display_notes(filtered)

    def _clear_search(self):
        self.search_input.clear()
        self.load_data()

    def _get_selected_note_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        id_item = self.table.item(row, 0)
        return id_item.data(Qt.ItemDataRole.UserRole) if id_item else None

    def _open_new_note_dialog(self):
        dlg = NoteEditorDialog(
            parent=self,
            note_id=None,
            default_project_id=self._active_project_id,
        )
        if dlg.exec():
            self.load_data()
            self.note_changed.emit()

    def _open_edit_note_dialog(self, *args):
        if args and hasattr(args[0], "row"):
            self.table.selectRow(args[0].row())
        note_id = self._get_selected_note_id()
        if not note_id:
            QMessageBox.information(self, "Selection Required", "Please select a note to edit.")
            return

        dlg = NoteEditorDialog(
            parent=self,
            note_id=note_id,
            default_project_id=self._active_project_id,
        )
        if dlg.exec():
            self.load_data()
            self.note_changed.emit()

    def _delete_note(self):
        note_id = self._get_selected_note_id()
        if not note_id:
            QMessageBox.information(self, "Selection Required", "Please select a note to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this note?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            DataRepository.delete_document(note_id)
            self.load_data()
            self.note_changed.emit()

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        self.table.selectRow(row)

        menu = QMenu(self)
        action_edit = menu.addAction(IconHelper.get_icon("edit", 16), "Edit Note...")
        action_edit.triggered.connect(self._open_edit_note_dialog)

        action_delete = menu.addAction(IconHelper.get_icon("delete", 16), "Delete Note")
        action_delete.triggered.connect(self._delete_note)

        menu.addSeparator()

        action_refresh = menu.addAction(IconHelper.get_icon("refresh", 16), "Refresh List")
        action_refresh.triggered.connect(self.load_data)

        menu.exec(self.table.viewport().mapToGlobal(pos))
