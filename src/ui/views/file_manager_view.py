"""
File Manager & TempPad View for DigitalBrainEX AI.
Displays temporary files, auto-captured screenshots, and files from watch folders.
Enables instant preview and conversion to permanent project documents.
"""
import os
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSplitter,
    QTextEdit,
    QComboBox,
    QMessageBox,
    QFileDialog,
    QMenu,
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QMimeData
from PyQt6.QtGui import QPixmap, QAction
from src.config import TEMP_PAD_DIR
from src.core.repository import DataRepository
from src.core.event_bus import event_bus, EVT_WATCH_FOLDER_FILE
from src.ui.icons import IconHelper
from src.core.logger import logger


class FileManagerView(QWidget):
    file_converted = pyqtSignal()
    watch_folder_file_arrived = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewContentWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._current_file_path = None
        self._files = []
        self._dismissed_paths = set()
        self._init_ui()
        self.load_data()

        # Listen for newly arrived files in watch folders
        self.watch_folder_file_arrived.connect(self._on_watch_folder_file_arrived)
        event_bus.subscribe(EVT_WATCH_FOLDER_FILE, self._on_watch_folder_event)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # Header bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        title_label = QLabel("File Manager")
        title_label.setObjectName("ViewTitleLabel")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setIcon(IconHelper.get_icon("refresh", 16))
        self.btn_refresh.clicked.connect(self.load_data)
        header_layout.addWidget(self.btn_refresh)

        self.btn_open_folder = QPushButton("Open TempPad Folder")
        self.btn_open_folder.setIcon(IconHelper.get_icon("file_manager", 16))
        self.btn_open_folder.clicked.connect(self._open_temppad_folder)
        header_layout.addWidget(self.btn_open_folder)

        main_layout.addLayout(header_layout)

        # Splitter: File List (left), Preview & Ingestion (right)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        table_container = QWidget()
        table_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Filename", "Size", "Modified", "Source"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 120)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.itemSelectionChanged.connect(self._on_table_row_selected)
        self.table.itemDoubleClicked.connect(self._on_table_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        table_layout.addWidget(self.table)
        self.splitter.addWidget(table_container)

        # Preview & Convert Panel
        self.preview_container = QWidget()
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(12, 0, 0, 0)
        preview_layout.setSpacing(10)

        # Header for preview panel with close button
        preview_header_layout = QHBoxLayout()
        preview_header_layout.setContentsMargins(0, 0, 0, 0)
        preview_header_layout.setSpacing(8)

        preview_title = QLabel("File Preview & Project Ingestion")
        preview_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        preview_header_layout.addWidget(preview_title)

        preview_header_layout.addStretch()

        self.btn_close_preview = QPushButton("✕")
        self.btn_close_preview.setToolTip("Close Preview Pane")
        self.btn_close_preview.setFixedSize(26, 26)
        self.btn_close_preview.setStyleSheet(
            "QPushButton { font-weight: bold; border-radius: 4px; border: 1px solid #cbd5e1; background: #f8fafc; color: #475569; }"
            "QPushButton:hover { background: #fee2e2; color: #dc2626; border-color: #fca5a5; }"
        )
        self.btn_close_preview.clicked.connect(self._close_preview_pane)
        preview_header_layout.addWidget(self.btn_close_preview)

        preview_layout.addLayout(preview_header_layout)

        self.lbl_selected_file = QLabel("Select a file to preview")
        self.lbl_selected_file.setStyleSheet("color: #64748b; font-weight: 500;")
        preview_layout.addWidget(self.lbl_selected_file)

        # Image preview or text preview
        self.preview_image = QLabel()
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image.setStyleSheet("border: 1px dashed #cbd5e1; border-radius: 6px; min-height: 200px;")
        preview_layout.addWidget(self.preview_image)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.hide()
        preview_layout.addWidget(self.preview_text)

        # Conversion section
        convert_box = QWidget()
        convert_box.setObjectName("CardWidget")
        convert_layout = QVBoxLayout(convert_box)
        convert_layout.setContentsMargins(8, 8, 8, 8)
        convert_layout.setSpacing(6)

        convert_layout.addWidget(QLabel("Convert to Project Document:"))

        assign_layout = QHBoxLayout()
        assign_layout.addWidget(QLabel("Project:"))
        self.combo_proj = QComboBox()
        self._populate_projects()
        assign_layout.addWidget(self.combo_proj)

        assign_layout.addWidget(QLabel("Category:"))
        self.combo_cat = QComboBox()
        self._populate_categories()
        assign_layout.addWidget(self.combo_cat)
        convert_layout.addLayout(assign_layout)

        action_layout = QHBoxLayout()
        self.btn_convert = QPushButton("Save to Documents")
        self.btn_convert.setIcon(IconHelper.get_icon("save", 16))
        self.btn_convert.setObjectName("PrimaryButton")
        self.btn_convert.clicked.connect(self._convert_to_document)
        action_layout.addWidget(self.btn_convert)

        self.btn_open_external = QPushButton("Open in App")
        self.btn_open_external.setIcon(IconHelper.get_icon("open", 16))
        self.btn_open_external.clicked.connect(self._open_file_in_os)
        action_layout.addWidget(self.btn_open_external)

        self.btn_delete_file = QPushButton("Delete File")
        self.btn_delete_file.setIcon(IconHelper.get_icon("delete", 16))
        self.btn_delete_file.setObjectName("DangerButton")
        self.btn_delete_file.clicked.connect(self._delete_file)
        action_layout.addWidget(self.btn_delete_file)

        convert_layout.addLayout(action_layout)
        preview_layout.addWidget(convert_box)

        self.splitter.addWidget(self.preview_container)
        # By default, hide the preview/details pane
        self.preview_container.hide()
        self.splitter.setSizes([1000, 0])
        main_layout.addWidget(self.splitter)

    def _close_preview_pane(self):
        """Hides the preview container and restores full width to file table."""
        self.preview_container.hide()
        self.splitter.setSizes([1000, 0])

    def _show_preview_pane(self):
        """Shows the preview container if it was hidden."""
        if self.preview_container.isHidden():
            self.preview_container.show()
            self.splitter.setSizes([600, 400])

    def _populate_projects(self):
        self.combo_proj.clear()
        self.combo_proj.addItem("General", userData=0)
        try:
            projs = DataRepository.get_all_projects()
            for p in projs:
                name = p.ProjectName.strip() if p.ProjectName else f"Project #{p.PojectID}"
                self.combo_proj.addItem(name, userData=p.PojectID)
        except Exception as e:
            logger.error(f"Error populating file manager projects: {e}")

    def _populate_categories(self):
        self.combo_cat.clear()
        try:
            cats = DataRepository.get_document_categories()
            for c in cats:
                if c.CatogoryName:
                    self.combo_cat.addItem(c.CatogoryName)
        except Exception as e:
            logger.error(f"Error populating file manager categories: {e}")

    def load_data(self):
        """Scans TempPad folder and database WatchFolders for files."""
        self.table.setRowCount(0)
        self._files = []

        scan_dirs = [
            (TEMP_PAD_DIR, "TempPad"),
        ]

        # Scan database WatchFolders
        watch_folders = DataRepository.get_watch_folders()
        for wf in watch_folders:
            if os.path.exists(wf):
                scan_dirs.append((Path(wf), "WatchFolder"))

        for sdir, source in scan_dirs:
            if not os.path.exists(sdir):
                continue
            try:
                for entry in os.scandir(sdir):
                    if entry.is_file():
                        name = entry.name
                        # Skip office lock files (e.g. ~$Doc.docx) and hidden files
                        if name.startswith("~") or name.startswith("."):
                            continue
                        # Never display clipboard images or screenshots in File Manager
                        if name.startswith("ClipImage_") or name.startswith("Screenshot_"):
                            continue
                        # Skip temporary download artifacts
                        ext = os.path.splitext(name)[1].lower()
                        if ext in (".tmp", ".crdownload", ".part"):
                            continue

                        # Exclude dismissed files
                        norm_path = os.path.normpath(entry.path)
                        if norm_path in self._dismissed_paths:
                            continue
                        stat = entry.stat()
                        mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                        size_kb = f"{stat.st_size / 1024:.1f} KB"
                        self._files.append({
                            "name": entry.name,
                            "path": entry.path,
                            "size": size_kb,
                            "modified": mod_time,
                            "source": source,
                        })
            except Exception as e:
                logger.error(f"Error scanning directory {sdir}: {e}")

        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(self._files))
            for row, f in enumerate(self._files):
                name_item = QTableWidgetItem(f["name"])
                name_item.setData(Qt.ItemDataRole.UserRole, f["path"])
                size_item = QTableWidgetItem(f["size"])
                mod_item = QTableWidgetItem(f["modified"])
                src_item = QTableWidgetItem(f["source"])

                for item in (name_item, size_item, mod_item, src_item):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.table.setItem(row, 0, name_item)
                self.table.setItem(row, 1, size_item)
                self.table.setItem(row, 2, mod_item)
                self.table.setItem(row, 3, src_item)
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)

    def _get_selected_file_paths(self):
        """Returns a list of distinct file paths for all currently selected rows."""
        selected_indexes = self.table.selectionModel().selectedRows()
        paths = []
        for idx in selected_indexes:
            item = self.table.item(idx.row(), 0)
            if item:
                path = item.data(Qt.ItemDataRole.UserRole)
                if path and path not in paths:
                    paths.append(path)
        return paths

    def _on_table_double_clicked(self, item):
        """Double clicking a row immediately opens the file in its default application."""
        if not item:
            return
        row = item.row()
        name_item = self.table.item(row, 0)
        if not name_item:
            return
        file_path = name_item.data(Qt.ItemDataRole.UserRole)
        if file_path and os.path.exists(file_path):
            try:
                os.startfile(file_path)
            except Exception as e:
                QMessageBox.warning(self, "Open Error", f"Could not open file:\n{e}")

    def _on_table_row_selected(self):
        selected_paths = self._get_selected_file_paths()
        if not selected_paths:
            return

        # Reveal the preview panel when a file is clicked/selected
        self._show_preview_pane()

        # Update preview using the primary / first selected file
        file_path = selected_paths[0]
        self._current_file_path = file_path

        if len(selected_paths) > 1:
            self.lbl_selected_file.setText(f"{os.path.basename(file_path)} (+ {len(selected_paths) - 1} more selected)")
        else:
            self.lbl_selected_file.setText(os.path.basename(file_path))

        if not os.path.exists(file_path):
            self.preview_image.setText("File does not exist")
            self.preview_image.show()
            self.preview_text.hide()
            return

        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(400, 240, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.preview_image.setPixmap(scaled)
                self.preview_image.show()
                self.preview_text.hide()
            else:
                self.preview_image.setText("Cannot render image preview")
                self.preview_image.show()
                self.preview_text.hide()
        elif ext in (".txt", ".log", ".md", ".json", ".py", ".cs", ".sql", ".csv"):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(5000)
                self.preview_text.setPlainText(content)
                self.preview_text.show()
                self.preview_image.hide()
            except Exception as e:
                self.preview_image.setText(f"Error previewing file: {e}")
                self.preview_image.show()
                self.preview_text.hide()
        else:
            self.preview_image.setText(f"Preview not available for {ext} file\nDouble-click or click 'Open in App' to view.")
            self.preview_image.show()
            self.preview_text.hide()

    def _show_context_menu(self, pos):
        """Displays right-click context menu for selected file(s)."""
        selected_paths = self._get_selected_file_paths()
        if not selected_paths:
            # Check if right-click was on a specific row
            item = self.table.itemAt(pos)
            if item:
                self.table.selectRow(item.row())
                selected_paths = self._get_selected_file_paths()
            else:
                return

        menu = QMenu(self)

        # Open action
        action_open = menu.addAction(IconHelper.get_icon("open", 16), "Open")
        action_open.triggered.connect(self._open_file_in_os)

        menu.addSeparator()

        # Copy Path
        action_copy_path = menu.addAction(IconHelper.get_icon("copy", 16), "Copy Path")
        action_copy_path.triggered.connect(self._copy_selected_paths)

        # Copy File (to OS clipboard)
        action_copy_file = menu.addAction(IconHelper.get_icon("file_manager", 16), "Copy File")
        action_copy_file.triggered.connect(self._copy_selected_files_to_clipboard)

        menu.addSeparator()

        # Delete action
        action_delete = menu.addAction(IconHelper.get_icon("delete", 16), f"Delete ({len(selected_paths)} item{'s' if len(selected_paths) > 1 else ''})")
        action_delete.triggered.connect(self._delete_file)

        if len(selected_paths) == 1:
            menu.addSeparator()
            action_convert = menu.addAction(IconHelper.get_icon("save", 16), "Save to Documents")
            action_convert.triggered.connect(self._convert_to_document)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _copy_selected_paths(self):
        """Copies full paths of selected files to clipboard."""
        selected_paths = self._get_selected_file_paths()
        if not selected_paths:
            return
        text = "\n".join(selected_paths)
        QApplication.clipboard().setText(text)

    def _copy_selected_files_to_clipboard(self):
        """Copies selected files to the system clipboard so they can be pasted in Windows Explorer."""
        selected_paths = self._get_selected_file_paths()
        if not selected_paths:
            return
        mime = QMimeData()
        valid_paths = [p for p in selected_paths if os.path.exists(p)]
        urls = [QUrl.fromLocalFile(p) for p in valid_paths]
        if urls:
            mime.setUrls(urls)
            mime.setText("\n".join(valid_paths))
            QApplication.clipboard().setMimeData(mime)

    def _convert_to_document(self):
        selected_paths = self._get_selected_file_paths()
        target_path = selected_paths[0] if selected_paths else self._current_file_path
        if not target_path or not os.path.exists(target_path):
            QMessageBox.warning(self, "Select File", "Please select a valid file to save.")
            return

        proj_id = self.combo_proj.currentData() or 0
        proj_name = self.combo_proj.currentText()
        cat = self.combo_cat.currentText() or "General"
        fname = os.path.basename(target_path)

        DataRepository.create_document(
            name=fname,
            uri=target_path,
            desc=f"Imported from {os.path.dirname(target_path)}",
            project_id=proj_id,
            project_name=proj_name,
            category=cat,
            doc_type=0,
        )
        QMessageBox.information(self, "Success", f"File '{fname}' successfully added to Documents catalog!")
        self.file_converted.emit()

    def _open_file_in_os(self):
        selected_paths = self._get_selected_file_paths()
        if not selected_paths and self._current_file_path:
            selected_paths = [self._current_file_path]

        for p in selected_paths:
            if os.path.exists(p):
                try:
                    os.startfile(p)
                except Exception as e:
                    logger.error(f"Error opening file {p}: {e}")

    def _open_temppad_folder(self):
        os.startfile(str(TEMP_PAD_DIR))

    def _delete_file(self):
        """
        Batched delete handler for single or multiple selected files.
        Asks only once with clear options:
        - Remove from File Manager only (keeps file on disk)
        - Delete permanently from Local Folder/Disk
        - Cancel
        """
        selected_paths = self._get_selected_file_paths()
        if not selected_paths and self._current_file_path:
            selected_paths = [self._current_file_path]

        if not selected_paths:
            QMessageBox.warning(self, "No Selection", "Please select file(s) to delete.")
            return

        count = len(selected_paths)
        if count == 1:
            fname = os.path.basename(selected_paths[0])
            msg_text = f"You have selected 1 file:\n'{fname}'\n\nHow would you like to delete it?"
        else:
            sample_names = ", ".join(f"'{os.path.basename(p)}'" for p in selected_paths[:3])
            if count > 3:
                sample_names += f" and {count - 3} more"
            msg_text = f"You have selected {count} files ({sample_names}).\n\nHow would you like to delete them?"

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Delete Options")
        msg_box.setText(msg_text)
        msg_box.setIcon(QMessageBox.Icon.Question)

        btn_remove_only = msg_box.addButton("Remove from File Manager", QMessageBox.ButtonRole.ActionRole)
        btn_delete_disk = msg_box.addButton("Delete from Disk", QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        msg_box.setDefaultButton(btn_cancel)

        msg_box.exec()
        clicked_button = msg_box.clickedButton()

        if clicked_button == btn_cancel or clicked_button is None:
            return

        if clicked_button == btn_remove_only:
            # Dismiss from file manager view without removing from disk
            for p in selected_paths:
                self._dismissed_paths.add(os.path.normpath(p))
            self.load_data()
            if self._current_file_path in selected_paths:
                self._current_file_path = None
                self._close_preview_pane()

        elif clicked_button == btn_delete_disk:
            # Permanently delete from disk
            failed = []
            for p in selected_paths:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception as e:
                        failed.append((os.path.basename(p), str(e)))
            self.load_data()
            if self._current_file_path in selected_paths:
                self._current_file_path = None
                self._close_preview_pane()

            if failed:
                err_details = "\n".join(f"- {name}: {err}" for name, err in failed)
                QMessageBox.critical(self, "Delete Errors", f"Failed to delete {len(failed)} file(s):\n{err_details}")

    def _on_watch_folder_event(self, file_path=None, **kwargs):
        """Thread-safe forwarder: Called when FolderWatcher emits EVT_WATCH_FOLDER_FILE."""
        self.watch_folder_file_arrived.emit(str(file_path or ""))

    def _on_watch_folder_file_arrived(self, file_path: str):
        """Runs on Qt main thread to immediately show newly arrived watch folder files."""
        logger.info(f"FileManagerView: Watch folder file arrived: {file_path}")
        self.load_data()

    def closeEvent(self, event):
        event_bus.unsubscribe(EVT_WATCH_FOLDER_FILE, self._on_watch_folder_event)
        super().closeEvent(event)

