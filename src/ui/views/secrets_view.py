"""
Secrets Vault View for DigitalBrainEX AI.
Full-width table matching original Secrets.cs with separate SecretEditorDialog modal.
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
from src.ui.dialogs.secret_editor_dlg import SecretEditorDialog
from src.ui.icons import IconHelper
from src.core.logger import logger


class SecretsView(QWidget):
    secret_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewContentWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._active_project_id = 0
        self._secrets = []
        self._init_ui()
        self.load_data()

        event_bus.subscribe(EVT_PROJECT_CHANGED, self._on_global_project_changed)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. Title
        title_label = QLabel("Secrets Vault")
        title_label.setObjectName("ViewTitleLabel")
        main_layout.addWidget(title_label)

        # 2. Search Row
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        lbl_search = QLabel("Search")
        search_layout.addWidget(lbl_search)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search secrets...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._filter_secrets)
        self.search_input.returnPressed.connect(self._filter_secrets)
        search_layout.addWidget(self.search_input)

        self.btn_go = QPushButton("Go")
        self.btn_go.setIcon(IconHelper.get_icon("search", 16))
        self.btn_go.clicked.connect(self._filter_secrets)
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
        self.btn_new.setToolTip("Store a new secret credential in popup dialog")
        self.btn_new.clicked.connect(self._open_new_secret_dialog)
        actions_layout.addWidget(self.btn_new)

        self.btn_edit = QPushButton("View / Edit")
        self.btn_edit.setIcon(IconHelper.get_icon("edit", 16))
        self.btn_edit.setToolTip("View or edit selected secret in popup dialog")
        self.btn_edit.clicked.connect(self._open_edit_secret_dialog)
        actions_layout.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setIcon(IconHelper.get_icon("delete", 16))
        self.btn_delete.setToolTip("Delete selected secret credential")
        self.btn_delete.clicked.connect(self._delete_secret)
        actions_layout.addWidget(self.btn_delete)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setIcon(IconHelper.get_icon("refresh", 16))
        self.btn_refresh.setToolTip("Reload secrets from database")
        self.btn_refresh.clicked.connect(self.load_data)
        actions_layout.addWidget(self.btn_refresh)

        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        # 4. Full-width Secrets Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Secret / Account Name", "Application / URL", "Project"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 65)
        self.table.setColumnWidth(1, 240)
        self.table.setColumnWidth(3, 160)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._open_edit_secret_dialog)
        main_layout.addWidget(self.table)

    def _on_global_project_changed(self, project_id: int, project_name: str):
        self._active_project_id = project_id
        self.load_data()

    def _get_selected_secret_id(self) -> Optional[int]:
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return None
        row = self.table.currentRow()
        id_item = self.table.item(row, 0)
        if not id_item:
            return None
        return id_item.data(Qt.ItemDataRole.UserRole)

    def _open_new_secret_dialog(self, *args):
        dlg = SecretEditorDialog(parent=self, default_project_id=self._active_project_id, mode="add")
        if dlg.exec():
            self.load_data()
            self.secret_changed.emit()

    def _open_edit_secret_dialog(self, *args):
        if args and hasattr(args[0], "row"):
            self.table.selectRow(args[0].row())
        secret_id = self._get_selected_secret_id()
        if not secret_id:
            QMessageBox.information(self, "No Selection", "Please select a secret to view or edit.")
            return
        dlg = SecretEditorDialog(parent=self, secret_id=secret_id, default_project_id=self._active_project_id, mode="edit")
        if dlg.exec():
            self.load_data()
            self.secret_changed.emit()

    def load_data(self):
        proj_filter = str(self._active_project_id) if self._active_project_id != 0 else None
        try:
            self._secrets = DataRepository.get_secrets(project_id=proj_filter)
            self._display_secrets(self._secrets)
        except Exception as e:
            logger.error(f"Error loading secrets: {e}")

    def _display_secrets(self, secrets):
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(secrets))
            for row, s in enumerate(secrets):
                id_item = QTableWidgetItem(str(s.SecretID))
                id_item.setData(Qt.ItemDataRole.UserRole, s.SecretID)
                name_item = QTableWidgetItem(s.SecretName or "")
                url_item = QTableWidgetItem(s.ApplicationURL or "")
                proj_item = QTableWidgetItem(s.ProjectName or "General")

                for item in (id_item, name_item, url_item, proj_item):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.table.setItem(row, 0, id_item)
                self.table.setItem(row, 1, name_item)
                self.table.setItem(row, 2, url_item)
                self.table.setItem(row, 3, proj_item)
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)

    def _filter_secrets(self, *args):
        query = self.search_input.text().strip().lower()
        if not query:
            self._display_secrets(self._secrets)
            return
        terms = [t.strip() for t in query.split("+") if t.strip()]
        filtered = [
            s for s in self._secrets
            if all(
                term in (s.SecretName or "").lower()
                or term in (s.ApplicationURL or "").lower()
                or term in (s.Desc or "").lower()
                or term in (s.ProjectName or "").lower()
                for term in terms
            )
        ]
        self._display_secrets(filtered)

    def _clear_search(self):
        self.search_input.clear()
        self.load_data()

    def _delete_secret(self, *args):
        secret_id = self._get_selected_secret_id()
        if not secret_id:
            QMessageBox.information(self, "No Selection", "Please select a secret to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this secret credential?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            DataRepository.delete_secret(secret_id)
            self.load_data()
            self.secret_changed.emit()

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        self.table.selectRow(row)

        menu = QMenu(self)
        action_edit = menu.addAction(IconHelper.get_icon("edit", 16), "View / Edit Secret...")
        action_edit.triggered.connect(self._open_edit_secret_dialog)

        action_delete = menu.addAction(IconHelper.get_icon("delete", 16), "Delete Secret")
        action_delete.triggered.connect(self._delete_secret)

        menu.addSeparator()

        action_refresh = menu.addAction(IconHelper.get_icon("refresh", 16), "Refresh List")
        action_refresh.triggered.connect(self.load_data)

        menu.exec(self.table.viewport().mapToGlobal(pos))
