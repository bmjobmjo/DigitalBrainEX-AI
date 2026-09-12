"""
Meeting Minutes View for DigitalBrainEX AI.
Full-width table matching original Minutes.cs with separate MinutesEditorDialog modal.
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
from src.core.event_bus import event_bus, EVT_PROJECT_CHANGED
from src.ui.dialogs.minutes_editor_dlg import MinutesEditorDialog
from src.ui.icons import IconHelper
from src.config import resolve_document_path, open_path_or_url
from src.core.logger import logger


class MinutesView(QWidget):
    minutes_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewContentWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._active_project_id = 0
        self._minutes = []
        self._init_ui()
        self.load_data()

        event_bus.subscribe(EVT_PROJECT_CHANGED, self._on_global_project_changed)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. Title
        title_label = QLabel("Meeting Minutes")
        title_label.setObjectName("ViewTitleLabel")
        main_layout.addWidget(title_label)

        # 2. Search Row
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        lbl_search = QLabel("Search")
        search_layout.addWidget(lbl_search)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search minutes...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._filter_minutes)
        self.search_input.returnPressed.connect(self._filter_minutes)
        search_layout.addWidget(self.search_input)

        self.btn_go = QPushButton("Go")
        self.btn_go.setIcon(IconHelper.get_icon("search", 16))
        self.btn_go.clicked.connect(self._filter_minutes)
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
        self.btn_new.setToolTip("Create new meeting minutes in popup dialog")
        self.btn_new.clicked.connect(self._open_new_minutes_dialog)
        actions_layout.addWidget(self.btn_new)

        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setIcon(IconHelper.get_icon("edit", 16))
        self.btn_edit.setToolTip("Edit selected meeting minutes in popup dialog")
        self.btn_edit.clicked.connect(self._open_edit_minutes_dialog)
        actions_layout.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setIcon(IconHelper.get_icon("delete", 16))
        self.btn_delete.setToolTip("Delete selected meeting minutes")
        self.btn_delete.clicked.connect(self._delete_minutes)
        actions_layout.addWidget(self.btn_delete)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setIcon(IconHelper.get_icon("refresh", 16))
        self.btn_refresh.setToolTip("Reload meeting minutes from database")
        self.btn_refresh.clicked.connect(self.load_data)
        actions_layout.addWidget(self.btn_refresh)

        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        # 4. Full-width Minutes Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Meeting Subject", "Project", "Date / Time", "Audio"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 65)
        self.table.setColumnWidth(2, 160)
        self.table.setColumnWidth(3, 140)
        self.table.setColumnWidth(4, 90)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._open_edit_minutes_dialog)
        main_layout.addWidget(self.table)

    def _on_global_project_changed(self, project_id: int, project_name: str):
        self._active_project_id = project_id
        self.load_data()

    def _get_selected_minute_id(self) -> Optional[int]:
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return None
        row = self.table.currentRow()
        id_item = self.table.item(row, 0)
        if not id_item:
            return None
        return id_item.data(Qt.ItemDataRole.UserRole)

    def _open_new_minutes_dialog(self):
        dlg = MinutesEditorDialog(parent=self, default_project_id=self._active_project_id)
        if dlg.exec():
            self.load_data()
            self.minutes_changed.emit()

    def _open_edit_minutes_dialog(self):
        minute_id = self._get_selected_minute_id()
        if not minute_id:
            QMessageBox.information(self, "No Selection", "Please select a meeting minute to edit.")
            return
        dlg = MinutesEditorDialog(parent=self, minute_id=minute_id, default_project_id=self._active_project_id)
        if dlg.exec():
            self.load_data()
            self.minutes_changed.emit()

    def load_data(self):
        proj_filter = self._active_project_id if self._active_project_id != 0 else None
        try:
            self._minutes = DataRepository.get_minutes(project_id=proj_filter)
            self._display_minutes(self._minutes)
        except Exception as e:
            logger.error(f"Error loading meeting minutes: {e}")

    def _display_minutes(self, minutes):
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(minutes))
            for row, m in enumerate(minutes):
                id_item = QTableWidgetItem(str(m.DocumentID))
                id_item.setData(Qt.ItemDataRole.UserRole, m.DocumentID)
                subject_item = QTableWidgetItem(m.DocumentName or "")
                proj_item = QTableWidgetItem(m.ProjectName or "General")
                date_item = QTableWidgetItem(m.AddedOn or "")
                audio_item = QTableWidgetItem("🎙️ Yes" if m.DocumentURI else "No")

                for item in (id_item, subject_item, proj_item, date_item, audio_item):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.table.setItem(row, 0, id_item)
                self.table.setItem(row, 1, subject_item)
                self.table.setItem(row, 2, proj_item)
                self.table.setItem(row, 3, date_item)
                self.table.setItem(row, 4, audio_item)
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)

    def _filter_minutes(self, *args):
        query = self.search_input.text().strip().lower()
        if not query:
            self._display_minutes(self._minutes)
            return
        filtered = [
            m for m in self._minutes
            if query in (m.DocumentName or "").lower()
            or query in (m.Notes or "").lower()
            or query in (m.Desc or "").lower()
        ]
        self._display_minutes(filtered)

    def _clear_search(self):
        self.search_input.clear()
        self.load_data()

    def _delete_minutes(self):
        minute_id = self._get_selected_minute_id()
        if not minute_id:
            QMessageBox.information(self, "No Selection", "Please select a meeting minute to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this meeting minute?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            DataRepository.delete_document(minute_id)
            self.load_data()
            self.minutes_changed.emit()

    def _open_selected_audio(self):
        minute_id = self._get_selected_minute_id()
        if not minute_id:
            return
        doc = DataRepository.get_document_by_id(minute_id)
        if doc and doc.DocumentURI:
            resolved = resolve_document_path(doc.DocumentURI)
            open_path_or_url(resolved, self)
        else:
            QMessageBox.information(self, "No Audio", "This meeting minute does not have an attached audio recording.")

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        self.table.selectRow(row)

        menu = QMenu(self)
        action_audio = menu.addAction(IconHelper.get_icon("audio", 16), "Play / Open Audio Recording")
        action_audio.triggered.connect(self._open_selected_audio)

        menu.addSeparator()

        action_edit = menu.addAction(IconHelper.get_icon("edit", 16), "Edit Meeting Minutes...")
        action_edit.triggered.connect(self._open_edit_minutes_dialog)

        action_delete = menu.addAction(IconHelper.get_icon("delete", 16), "Delete Meeting Minutes")
        action_delete.triggered.connect(self._delete_minutes)

        menu.addSeparator()

        action_refresh = menu.addAction(IconHelper.get_icon("refresh", 16), "Refresh List")
        action_refresh.triggered.connect(self.load_data)

        menu.exec(self.table.viewport().mapToGlobal(pos))
