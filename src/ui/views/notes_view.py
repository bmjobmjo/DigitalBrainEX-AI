"""
Notes Listing & Multi-Tab Editor View for DigitalBrainEX AI.
Provides full-width notes catalog and multi-tab document editing with auto-save,
default note naming, in-tab Save/Close options, and name & category prompts.
"""
from typing import Optional
from datetime import datetime
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
    QTabWidget,
    QTabBar,
    QTextEdit,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut

from src.core.repository import DataRepository
from src.core.event_bus import event_bus, EVT_PROJECT_CHANGED
from src.ui.dialogs.save_note_dlg import SaveNoteMetadataDialog
from src.ui.icons import IconHelper
from src.core.logger import logger


class NoteTabEditor(QWidget):
    """
    Individual Tab Editor for a single note.
    Includes in-tab Save, Close, debounced auto-save, and metadata displays.
    """
    saved = pyqtSignal(int)          # emits note_id
    title_changed = pyqtSignal(str)  # emits updated title
    close_requested = pyqtSignal()   # requests tab closure

    def __init__(
        self,
        parent=None,
        note_id: Optional[int] = None,
        default_title: str = "Note 1",
        default_project_id: int = 0,
    ):
        super().__init__(parent)
        self.note_id: Optional[int] = note_id
        self.title: str = default_title
        self.category: str = "PlainNotes"
        self.project_id: int = default_project_id
        self.project_name: str = "General"
        self.is_dirty: bool = False

        # Debounced Auto-Save Timer (2 seconds after typing ceases)
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setSingleShot(True)
        self._auto_save_timer.setInterval(2000)
        self._auto_save_timer.timeout.connect(self.auto_save)

        self._init_ui()

        if self.note_id:
            self._load_existing_note()
        else:
            self._resolve_project_name()
            self._update_meta_labels()

        # Keyboard Shortcut: Ctrl+S saves note
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(lambda: self.save_note(prompt_metadata=True))

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        # 1. In-Tab Top Toolbar
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("NoteToolbarFrame")
        toolbar_frame.setStyleSheet("""
            #NoteToolbarFrame {
                background-color: rgba(128, 128, 128, 0.08);
                border: 1px solid rgba(128, 128, 128, 0.2);
                border-radius: 6px;
                padding: 4px 8px;
            }
        """)
        tb_layout = QHBoxLayout(toolbar_frame)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(12)

        # Title display & Metadata chips
        self.lbl_title = QLabel(f"📝 {self.title}")
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: bold;")
        tb_layout.addWidget(self.lbl_title)

        self.lbl_meta = QLabel()
        self.lbl_meta.setStyleSheet("font-size: 11px; opacity: 0.8; color: #888888;")
        tb_layout.addWidget(self.lbl_meta)

        tb_layout.addStretch()

        # Auto-Save status indicator
        self.lbl_status = QLabel("● Saved")
        self.lbl_status.setStyleSheet("color: #98c379; font-size: 11px; font-weight: 500;")
        tb_layout.addWidget(self.lbl_status)

        # Save Button
        self.btn_save = QPushButton("Save")
        self.btn_save.setIcon(IconHelper.get_icon("save", 16))
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.setToolTip("Save Note & Configure Title / Category (Ctrl+S)")
        self.btn_save.clicked.connect(lambda: self.save_note(prompt_metadata=True))
        tb_layout.addWidget(self.btn_save)

        # Close Button
        self.btn_close = QPushButton("Close")
        self.btn_close.setIcon(IconHelper.get_icon("clear", 16))
        self.btn_close.setToolTip("Close this note tab")
        self.btn_close.clicked.connect(self.close_requested.emit)
        tb_layout.addWidget(self.btn_close)

        layout.addWidget(toolbar_frame)

        # 2. Main Note Body Editor
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Write your notes, diary entry, logs, or thoughts here...")
        self.editor.setStyleSheet("""
            QTextEdit {
                font-size: 12px;
                line-height: 1.4;
                padding: 10px;
                border: 1px solid rgba(128, 128, 128, 0.25);
                border-radius: 6px;
            }
        """)
        self.editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.editor, stretch=1)

    def _resolve_project_name(self):
        if self.project_id == 0:
            self.project_name = "General"
            return
        try:
            projects = DataRepository.get_all_projects()
            for p in projects:
                if p.PojectID == self.project_id:
                    self.project_name = p.ProjectName.strip() if p.ProjectName else f"Project #{p.PojectID}"
                    return
        except Exception as e:
            logger.error(f"Error resolving project name for note: {e}")
        self.project_name = "General"

    def _update_meta_labels(self):
        self.lbl_title.setText(f"📝 {self.title}")
        self.lbl_meta.setText(f"🏷️ Category: {self.category}  |  📁 Project: {self.project_name}")

    def _load_existing_note(self):
        try:
            doc = DataRepository.get_document_by_id(self.note_id)
            if doc:
                self.title = doc.DocumentName or f"Note #{self.note_id}"
                self.category = doc.Category or "PlainNotes"
                self.project_id = doc.PojectID or 0
                self.project_name = doc.ProjectName or "General"
                content = doc.Desc if doc.Desc else (doc.Notes or "")

                self.editor.blockSignals(True)
                self.editor.setPlainText(content)
                self.editor.blockSignals(False)

                self.is_dirty = False
                self.lbl_status.setText("● Saved")
                self.lbl_status.setStyleSheet("color: #98c379; font-size: 11px; font-weight: 500;")
                self._update_meta_labels()
        except Exception as e:
            logger.error(f"Error loading note {self.note_id}: {e}")

    def _on_text_changed(self):
        self.is_dirty = True
        self.lbl_status.setText("● Unsaved changes...")
        self.lbl_status.setStyleSheet("color: #e5c07b; font-size: 11px; font-weight: 500;")
        self._auto_save_timer.start()

    def save_note(self, prompt_metadata: bool = True) -> bool:
        """
        Saves the note to the database. If prompt_metadata is True, opens SaveNoteMetadataDialog
        to allow user to customize the note title, category, and project.
        """
        if prompt_metadata:
            res = SaveNoteMetadataDialog.prompt(
                parent=self,
                initial_title=self.title,
                initial_category=self.category,
                initial_project_id=self.project_id,
            )
            if not res:
                return False
            title, cat, proj_id, proj_name = res
            self.title = title
            self.category = cat
            self.project_id = proj_id
            self.project_name = proj_name

        content = self.editor.toPlainText()
        try:
            if self.note_id:
                DataRepository.update_document(
                    self.note_id,
                    DocumentName=self.title,
                    Desc=content,
                    Notes=content,
                    Category=self.category,
                    PojectID=self.project_id,
                    ProjectName=self.project_name,
                )
            else:
                new_doc = DataRepository.create_document(
                    name=self.title,
                    desc=content,
                    notes=content,
                    project_id=self.project_id,
                    project_name=self.project_name,
                    category=self.category,
                    doc_type=2,
                )
                self.note_id = new_doc.DocumentID

            self.is_dirty = False
            self._update_meta_labels()
            now_str = datetime.now().strftime("%H:%M:%S")
            self.lbl_status.setText(f"● Saved at {now_str}")
            self.lbl_status.setStyleSheet("color: #98c379; font-size: 11px; font-weight: 500;")
            self.title_changed.emit(self.title)
            self.saved.emit(self.note_id)
            return True
        except Exception as e:
            logger.error(f"Error saving note: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save note: {e}")
            return False

    def auto_save(self):
        """Silently auto-saves current note content to database without popping up modal dialogs."""
        content = self.editor.toPlainText()
        if not content.strip() and not self.note_id:
            return

        try:
            if self.note_id:
                DataRepository.update_document(
                    self.note_id,
                    Desc=content,
                    Notes=content,
                )
            else:
                new_doc = DataRepository.create_document(
                    name=self.title,
                    desc=content,
                    notes=content,
                    project_id=self.project_id,
                    project_name=self.project_name,
                    category=self.category,
                    doc_type=2,
                )
                self.note_id = new_doc.DocumentID

            self.is_dirty = False
            now_str = datetime.now().strftime("%H:%M:%S")
            self.lbl_status.setText(f"● Auto-saved at {now_str}")
            self.lbl_status.setStyleSheet("color: #98c379; font-size: 11px; font-weight: 500;")
            self.saved.emit(self.note_id)
        except Exception as e:
            logger.error(f"Error during auto-save of note: {e}")

    def can_close(self) -> bool:
        """Checks if tab can safely be closed; prompts user if unsaved changes exist."""
        if self.is_dirty:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"You have unsaved changes in '{self.title}'.\nDo you want to save before closing?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if reply == QMessageBox.StandardButton.Save:
                return self.save_note(prompt_metadata=True)
            elif reply == QMessageBox.StandardButton.Discard:
                # Clean up blank draft if created during auto-save
                if self.note_id and not self.editor.toPlainText().strip():
                    try:
                        DataRepository.delete_document(self.note_id)
                        self.saved.emit(self.note_id)
                    except Exception:
                        pass
                return True
            else:
                return False

        # Clean up empty draft if any
        if self.note_id and not self.editor.toPlainText().strip():
            try:
                DataRepository.delete_document(self.note_id)
                self.saved.emit(self.note_id)
            except Exception:
                pass
        return True

    def focus_editor(self):
        self.editor.setFocus()


class NotesView(QWidget):
    """
    Main Personal Diary & Notes module with persistent catalog list tab and
    dynamic, closable tabs for individual notes.
    """
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
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Tab Widget container
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self._on_tab_close_requested)
        self.tab_widget.currentChanged.connect(lambda _: self._ensure_tab_0_not_closable())

        # Tab Bar Corner Widget: + New Note
        self.btn_tab_new = QPushButton("  + New Note  ")
        self.btn_tab_new.setIcon(IconHelper.get_icon("add", 16))
        self.btn_tab_new.setToolTip("Create a new note tab (Ctrl+N)")
        self.btn_tab_new.clicked.connect(self.create_new_note_tab)
        self.tab_widget.setCornerWidget(self.btn_tab_new, Qt.Corner.TopRightCorner)

        # Shortcut Ctrl+N to open new note tab
        new_note_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_note_shortcut.activated.connect(self.create_new_note_tab)

        # --- Tab 0: Notes Catalog List ---
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(10, 8, 10, 8)
        list_layout.setSpacing(8)

        # 1. Title
        title_label = QLabel("Personal Diary & Notes")
        title_label.setObjectName("ViewTitleLabel")
        list_layout.addWidget(title_label)

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
        list_layout.addLayout(search_layout)

        # 3. Action Buttons Row
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)

        self.btn_new = QPushButton("Add")
        self.btn_new.setIcon(IconHelper.get_icon("add", 16))
        self.btn_new.setToolTip("Create a new note in a new tab")
        self.btn_new.clicked.connect(self.create_new_note_tab)
        actions_layout.addWidget(self.btn_new)

        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setIcon(IconHelper.get_icon("edit", 16))
        self.btn_edit.setToolTip("Open selected note in tab")
        self.btn_edit.clicked.connect(lambda: self.open_note_tab())
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
        list_layout.addLayout(actions_layout)

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
        self.table.doubleClicked.connect(lambda: self.open_note_tab())
        list_layout.addWidget(self.table)

        # Add Tab 0: Notes Catalog List
        self.tab_widget.addTab(list_container, IconHelper.get_icon("notes", 16), "📋 All Notes")
        self._ensure_tab_0_not_closable()

        main_layout.addWidget(self.tab_widget)

    def _ensure_tab_0_not_closable(self):
        """Ensures that Tab 0 (All Notes) does not display a close button."""
        tab_bar = self.tab_widget.tabBar()
        if tab_bar.count() > 0:
            tab_bar.setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
            tab_bar.setTabButton(0, QTabBar.ButtonPosition.LeftSide, None)

    def _generate_default_note_name(self) -> str:
        """Finds the next sequential default note name, e.g. Note 1, Note 2, Note 3..."""
        existing_names = set()
        for idx in range(1, self.tab_widget.count()):
            editor = self.tab_widget.widget(idx)
            if isinstance(editor, NoteTabEditor):
                existing_names.add(editor.title)
        for n in self._notes:
            if n.DocumentName:
                existing_names.add(n.DocumentName)

        counter = 1
        while f"Note {counter}" in existing_names:
            counter += 1
        return f"Note {counter}"

    def create_new_note_tab(self) -> NoteTabEditor:
        """Creates and switches to a new Note tab named 'Note xxxx'."""
        default_name = self._generate_default_note_name()
        editor = NoteTabEditor(
            parent=self,
            note_id=None,
            default_title=default_name,
            default_project_id=self._active_project_id,
        )
        editor.close_requested.connect(lambda: self._close_editor_tab(editor))
        editor.saved.connect(self._on_note_saved)
        editor.title_changed.connect(lambda t: self._update_tab_title(editor, t))

        idx = self.tab_widget.addTab(editor, IconHelper.get_icon("notes", 16), default_name)
        self._ensure_tab_0_not_closable()
        self.tab_widget.setCurrentIndex(idx)
        editor.focus_editor()
        return editor

    def open_note_tab(self, note_id: Optional[int] = None) -> Optional[NoteTabEditor]:
        """
        Opens an existing note in a tab. If already open in an existing tab, activates it.
        """
        if note_id is None:
            note_id = self._get_selected_note_id()
        if not note_id:
            QMessageBox.information(self, "Selection Required", "Please select a note to open/edit.")
            return None

        # 1. Check if already open in a tab
        for idx in range(1, self.tab_widget.count()):
            editor = self.tab_widget.widget(idx)
            if isinstance(editor, NoteTabEditor) and editor.note_id == note_id:
                self.tab_widget.setCurrentIndex(idx)
                editor.focus_editor()
                return editor

        # 2. Otherwise open in a new tab
        editor = NoteTabEditor(
            parent=self,
            note_id=note_id,
            default_project_id=self._active_project_id,
        )
        editor.close_requested.connect(lambda: self._close_editor_tab(editor))
        editor.saved.connect(self._on_note_saved)
        editor.title_changed.connect(lambda t: self._update_tab_title(editor, t))

        idx = self.tab_widget.addTab(editor, IconHelper.get_icon("notes", 16), editor.title)
        self._ensure_tab_0_not_closable()
        self.tab_widget.setCurrentIndex(idx)
        editor.focus_editor()
        return editor

    def _on_tab_close_requested(self, index: int):
        if index <= 0:
            return  # Tab 0 cannot be closed

        editor = self.tab_widget.widget(index)
        if isinstance(editor, NoteTabEditor):
            if editor.can_close():
                self.tab_widget.removeTab(index)
                editor.deleteLater()
                self._ensure_tab_0_not_closable()

    def _close_editor_tab(self, editor: NoteTabEditor):
        idx = self.tab_widget.indexOf(editor)
        if idx > 0:
            self._on_tab_close_requested(idx)

    def _update_tab_title(self, editor: NoteTabEditor, new_title: str):
        idx = self.tab_widget.indexOf(editor)
        if idx > 0:
            self.tab_widget.setTabText(idx, new_title)

    def _on_note_saved(self, note_id: int):
        self.load_data()
        self.note_changed.emit()

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
        # Preserve current selection
        current_id = self._get_selected_note_id()

        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(notes))
            target_row = -1
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

                if current_id is not None and n.DocumentID == current_id:
                    target_row = row

            if target_row >= 0:
                self.table.selectRow(target_row)
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

    def _get_selected_note_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            selected_rows = self.table.selectionModel().selectedRows()
            if selected_rows:
                row = selected_rows[0].row()
        if row < 0:
            return None
        id_item = self.table.item(row, 0)
        return id_item.data(Qt.ItemDataRole.UserRole) if id_item else None

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

            # Close open tab for this note if present
            for idx in range(1, self.tab_widget.count()):
                editor = self.tab_widget.widget(idx)
                if isinstance(editor, NoteTabEditor) and editor.note_id == note_id:
                    self.tab_widget.removeTab(idx)
                    editor.deleteLater()
                    self._ensure_tab_0_not_closable()
                    break

            self.load_data()
            self.note_changed.emit()

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        self.table.selectRow(row)

        menu = QMenu(self)
        action_open = menu.addAction(IconHelper.get_icon("notes", 16), "Open in Tab")
        action_open.triggered.connect(lambda: self.open_note_tab())

        action_delete = menu.addAction(IconHelper.get_icon("delete", 16), "Delete Note")
        action_delete.triggered.connect(self._delete_note)

        menu.addSeparator()

        action_refresh = menu.addAction(IconHelper.get_icon("refresh", 16), "Refresh List")
        action_refresh.triggered.connect(self.load_data)

        menu.exec(self.table.viewport().mapToGlobal(pos))
