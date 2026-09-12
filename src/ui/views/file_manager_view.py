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
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from src.config import TEMP_PAD_DIR, SCREENSHOTS_DIR
from src.core.repository import DataRepository
from src.ui.icons import IconHelper
from src.core.logger import logger


class FileManagerView(QWidget):
    file_converted = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewContentWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._current_file_path = None
        self._files = []
        self._init_ui()
        self.load_data()

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

        # Splitter: File List (50%), Preview & Ingestion (50%)
        splitter = QSplitter(Qt.Orientation.Horizontal)

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
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.itemSelectionChanged.connect(self._on_table_row_selected)
        table_layout.addWidget(self.table)
        splitter.addWidget(table_container)

        # Preview & Convert Panel
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(12, 0, 0, 0)
        preview_layout.setSpacing(10)

        preview_title = QLabel("File Preview & Project Ingestion")
        preview_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        preview_layout.addWidget(preview_title)

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

        splitter.addWidget(preview_container)
        splitter.setSizes([500, 500])
        main_layout.addWidget(splitter)

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
        """Scans TempPad folder and Screenshots folder for files."""
        self.table.setRowCount(0)
        self._files = []

        scan_dirs = [
            (TEMP_PAD_DIR, "TempPad"),
            (SCREENSHOTS_DIR, "Screenshots"),
        ]

        # Also scan database WatchFolders
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

    def _on_table_row_selected(self):
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return
        row = self.table.currentRow()
        name_item = self.table.item(row, 0)
        if not name_item:
            return

        file_path = name_item.data(Qt.ItemDataRole.UserRole)
        self._current_file_path = file_path
        self.lbl_selected_file.setText(os.path.basename(file_path))

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
            self.preview_image.setText(f"Preview not available for {ext} file\nClick 'Open in App' to view.")
            self.preview_image.show()
            self.preview_text.hide()

    def _convert_to_document(self):
        if not self._current_file_path or not os.path.exists(self._current_file_path):
            QMessageBox.warning(self, "Select File", "Please select a file to save.")
            return

        proj_id = self.combo_proj.currentData() or 0
        proj_name = self.combo_proj.currentText()
        cat = self.combo_cat.currentText() or "General"
        fname = os.path.basename(self._current_file_path)

        new_doc = DataRepository.create_document(
            name=fname,
            uri=self._current_file_path,
            desc=f"Imported from {os.path.dirname(self._current_file_path)}",
            project_id=proj_id,
            project_name=proj_name,
            category=cat,
            doc_type=0,
        )
        QMessageBox.information(self, "Success", f"File '{fname}' successfully added to Documents catalog!")
        self.file_converted.emit()

    def _open_file_in_os(self):
        if self._current_file_path and os.path.exists(self._current_file_path):
            os.startfile(self._current_file_path)

    def _open_temppad_folder(self):
        os.startfile(str(TEMP_PAD_DIR))

    def _delete_file(self):
        if not self._current_file_path or not os.path.exists(self._current_file_path):
            return
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete:\n{os.path.basename(self._current_file_path)}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                os.remove(self._current_file_path)
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete file: {e}")
