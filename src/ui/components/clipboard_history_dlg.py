"""
Clipboard History Dialog for DigitalBrainEX AI.
Provides rich preview of clipboard entries:
1. Icon-sized image thumbnails in the history table.
2. Full live preview panel for text, images, and metadata.
3. Quick copy, save to notes, delete, and search filtering.
"""
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QApplication,
    QSplitter,
    QFrame,
    QStackedWidget,
    QPlainTextEdit,
    QScrollArea,
    QComboBox,
    QAbstractItemView,
    QWidget,
)
from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtGui import (
    QPixmap,
    QIcon,
    QColor,
    QPainter,
    QFont,
)

from src.core.repository import DataRepository
from src.core.models import ClipboardHistory
from src.core.logger import logger


class ClipboardHistoryDialog(QDialog):
    """Rich Clipboard History viewer with thumbnail previews, live preview pane, and management."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📋 Clipboard History")
        self.resize(960, 620)
        self.setMinimumSize(780, 480)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        import os
        from src.utils.win32_helper import apply_native_window_icon
        self._icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "app_icon.ico"))
        if os.path.exists(self._icon_path):
            self.setWindowIcon(QIcon(self._icon_path))

        self._history: List[ClipboardHistory] = []
        self._thumb_cache: Dict[str, QIcon] = {}
        self._init_ui()
        self.load_data()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "_icon_path") and os.path.exists(self._icon_path):
            from src.utils.win32_helper import apply_native_window_icon
            apply_native_window_icon(int(self.winId()), self._icon_path)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. Top Header & Search / Filter Bar
        # -------------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        title_label = QLabel("📋 Clipboard History")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Type filter dropdown
        type_lbl = QLabel("Filter:")
        type_lbl.setStyleSheet("color: #475569; font-weight: 500;")
        header_layout.addWidget(type_lbl)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Items", "All")
        self.filter_combo.addItem("🖼️ Images Only", "Image")
        self.filter_combo.addItem("📝 Text Only", "Text")
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        header_layout.addWidget(self.filter_combo)

        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search text or image name...")
        self.search_input.setFixedWidth(240)
        self.search_input.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.search_input)

        # Refresh button
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self.load_data)
        header_layout.addWidget(self.btn_refresh)

        main_layout.addLayout(header_layout)

        # -------------------------------------------------------------
        # 2. Main Horizontal Splitter (Table on Left, Preview on Right)
        # -------------------------------------------------------------
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        # --- Left Panel: Table ---
        table_container = QFrame()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(6)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Preview", "Content Summary", "Type", "Copied On"])
        self.table.setIconSize(QSize(48, 48))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(56)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 68)
        self.table.setColumnWidth(2, 85)
        self.table.setColumnWidth(3, 140)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.doubleClicked.connect(self._copy_selected_to_clipboard)

        table_layout.addWidget(self.table)
        self.splitter.addWidget(table_container)

        # --- Right Panel: Live Preview Pane ---
        self.preview_panel = QFrame()
        self.preview_panel.setObjectName("PreviewPanel")
        self.preview_panel.setStyleSheet(
            "#PreviewPanel { background-color: #ffffff; border: 1px solid #d0d7de; border-radius: 6px; }"
        )
        preview_layout = QVBoxLayout(self.preview_panel)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        preview_layout.setSpacing(8)

        # Preview header
        preview_hdr = QHBoxLayout()
        self.preview_title = QLabel("Preview")
        self.preview_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0f172a;")
        preview_hdr.addWidget(self.preview_title)

        self.preview_badge = QLabel("")
        self.preview_badge.setStyleSheet("color: #64748b; font-size: 11px;")
        preview_hdr.addWidget(self.preview_badge)
        preview_hdr.addStretch()
        preview_layout.addLayout(preview_hdr)

        # Stacked preview widget
        self.preview_stack = QStackedWidget()

        # Page 0: Image Preview
        page_img = QWidget()
        page_img_layout = QVBoxLayout(page_img)
        page_img_layout.setContentsMargins(0, 0, 0, 0)
        page_img_layout.setSpacing(8)

        self.img_scroll = QScrollArea()
        self.img_scroll.setWidgetResizable(True)
        self.img_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_scroll.setStyleSheet("QScrollArea { border: 1px solid #e2e8f0; background: #f8fafc; }")

        self.lbl_image_preview = QLabel()
        self.lbl_image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_scroll.setWidget(self.lbl_image_preview)
        page_img_layout.addWidget(self.img_scroll, 1)

        self.lbl_img_details = QLabel()
        self.lbl_img_details.setStyleSheet("color: #475569; font-size: 11px;")
        self.lbl_img_details.setWordWrap(True)
        page_img_layout.addWidget(self.lbl_img_details)

        img_actions = QHBoxLayout()
        self.btn_copy_img = QPushButton("📋 Copy Image")
        self.btn_copy_img.clicked.connect(self._copy_selected_to_clipboard)
        img_actions.addWidget(self.btn_copy_img)

        self.btn_open_img = QPushButton("🔍 Open Image")
        self.btn_open_img.clicked.connect(self._open_image_external)
        img_actions.addWidget(self.btn_open_img)

        self.btn_show_folder = QPushButton("📁 Show in Folder")
        self.btn_show_folder.clicked.connect(self._show_in_folder)
        img_actions.addWidget(self.btn_show_folder)
        img_actions.addStretch()
        page_img_layout.addLayout(img_actions)

        self.preview_stack.addWidget(page_img)

        # Page 1: Text Preview
        page_txt = QWidget()
        page_txt_layout = QVBoxLayout(page_txt)
        page_txt_layout.setContentsMargins(0, 0, 0, 0)
        page_txt_layout.setSpacing(8)

        self.txt_preview_edit = QPlainTextEdit()
        self.txt_preview_edit.setReadOnly(True)
        self.txt_preview_edit.setStyleSheet(
            "QPlainTextEdit { font-family: 'Segoe UI', Consolas, sans-serif; font-size: 13px; "
            "background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 6px; }"
        )
        page_txt_layout.addWidget(self.txt_preview_edit, 1)

        self.lbl_txt_details = QLabel()
        self.lbl_txt_details.setStyleSheet("color: #475569; font-size: 11px;")
        page_txt_layout.addWidget(self.lbl_txt_details)

        txt_actions = QHBoxLayout()
        self.btn_copy_txt = QPushButton("📋 Copy Text")
        self.btn_copy_txt.clicked.connect(self._copy_selected_to_clipboard)
        txt_actions.addWidget(self.btn_copy_txt)

        self.btn_save_note = QPushButton("💾 Save as Note")
        self.btn_save_note.clicked.connect(self._save_as_note)
        txt_actions.addWidget(self.btn_save_note)
        txt_actions.addStretch()
        page_txt_layout.addLayout(txt_actions)

        self.preview_stack.addWidget(page_txt)

        # Page 2: Empty Placeholder
        page_empty = QWidget()
        page_empty_layout = QVBoxLayout(page_empty)
        page_empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_empty = QLabel("Select an entry to view details and full preview.")
        lbl_empty.setStyleSheet("color: #94a3b8; font-size: 13px;")
        lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_empty_layout.addWidget(lbl_empty)
        self.preview_stack.addWidget(page_empty)

        preview_layout.addWidget(self.preview_stack, 1)
        self.splitter.addWidget(self.preview_panel)

        # Set initial splitter proportions: 58% table, 42% preview
        self.splitter.setSizes([550, 390])
        main_layout.addWidget(self.splitter, 1)

        # -------------------------------------------------------------
        # 3. Bottom Action Bar
        # -------------------------------------------------------------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_copy_global = QPushButton("📋 Copy to Clipboard")
        self.btn_copy_global.setStyleSheet("font-weight: bold;")
        self.btn_copy_global.clicked.connect(self._copy_selected_to_clipboard)
        btn_layout.addWidget(self.btn_copy_global)

        self.btn_save_doc_global = QPushButton("💾 Save as Note")
        self.btn_save_doc_global.clicked.connect(self._save_as_note)
        btn_layout.addWidget(self.btn_save_doc_global)

        self.btn_delete = QPushButton("🗑️ Delete")
        self.btn_delete.clicked.connect(self._delete_selected)
        btn_layout.addWidget(self.btn_delete)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #16a34a; font-weight: bold; padding-left: 10px;")
        btn_layout.addWidget(self.lbl_status)

        btn_layout.addStretch()

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)

        main_layout.addLayout(btn_layout)

    # -----------------------------------------------------------------
    # Data Loading and Display
    # -----------------------------------------------------------------
    def load_data(self):
        """Loads the most recent clipboard entries from SQLite."""
        try:
            filter_type = self.filter_combo.currentData()
            search_query = self.search_input.text().strip()
            self._history = DataRepository.get_clipboard_history(
                limit=150,
                search=search_query or None,
                content_type=filter_type if filter_type != "All" else None,
            )
            self._display_history(self._history)
        except Exception as e:
            logger.error(f"Error loading clipboard history: {e}", exc_info=True)

    def _display_history(self, history: List[ClipboardHistory]):
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(history))
            for row, item in enumerate(history):
                # 1. Preview Icon (Column 0)
                icon = self._get_or_create_thumbnail(item)
                icon_item = QTableWidgetItem()
                icon_item.setIcon(icon)
                icon_item.setData(Qt.ItemDataRole.UserRole, item.ID)
                icon_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # 2. Content Summary (Column 1)
                if item.ContentType == "Image":
                    filename = Path(item.ImagePath).name if item.ImagePath else "Captured Image"
                    summary_item = QTableWidgetItem(f"{filename}")
                    summary_item.setToolTip(item.ImagePath or "")
                else:
                    raw_text = (item.TextContent or "").strip().replace("\r", "")
                    # Show up to 2 lines or 80 characters
                    lines = raw_text.split("\n")
                    snippet = lines[0][:80]
                    if len(lines) > 1 and lines[1].strip():
                        snippet += f" ↵ {lines[1].strip()[:50]}"
                    if len(raw_text) > len(snippet):
                        snippet += "..."
                    summary_item = QTableWidgetItem(snippet or "[Empty Text]")
                    summary_item.setToolTip(raw_text[:300] if len(raw_text) > 300 else raw_text)

                # 3. Type (Column 2)
                type_str = "🖼️ Image" if item.ContentType == "Image" else "📝 Text"
                type_item = QTableWidgetItem(type_str)
                type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # 4. Copied On (Column 3)
                date_str = item.AddedOn or ""
                date_item = QTableWidgetItem(date_str)
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                for cell in (icon_item, summary_item, type_item, date_item):
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.table.setItem(row, 0, icon_item)
                self.table.setItem(row, 1, summary_item)
                self.table.setItem(row, 2, type_item)
                self.table.setItem(row, 3, date_item)

            if len(history) > 0:
                self.table.selectRow(0)
            else:
                self.preview_stack.setCurrentIndex(2)
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)

        # Trigger selection for first row if present
        if len(history) > 0:
            self._on_selection_changed()

    # -----------------------------------------------------------------
    # Thumbnail Generation & Caching
    # -----------------------------------------------------------------
    def _get_or_create_thumbnail(self, item: ClipboardHistory) -> QIcon:
        """Returns a cached 48x48 icon for the clipboard entry."""
        if item.ContentType == "Image" and item.ImagePath:
            path = item.ImagePath
            if path in self._thumb_cache:
                return self._thumb_cache[path]

            canvas = QPixmap(48, 48)
            canvas.fill(Qt.GlobalColor.transparent)
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Draw soft container background
            painter.setBrush(QColor("#f1f5f9"))
            painter.setPen(QColor("#cbd5e1"))
            painter.drawRoundedRect(1, 1, 46, 46, 4, 4)

            if os.path.exists(path):
                src = QPixmap(path)
                if not src.isNull():
                    thumb = src.scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    ox = (48 - thumb.width()) // 2
                    oy = (48 - thumb.height()) // 2
                    painter.drawPixmap(ox, oy, thumb)
                else:
                    painter.setPen(QColor("#94a3b8"))
                    painter.drawText(QRect(0, 0, 48, 48), Qt.AlignmentFlag.AlignCenter, "IMG")
            else:
                # Missing file placeholder
                painter.setPen(QColor("#ef4444"))
                painter.drawText(QRect(0, 0, 48, 48), Qt.AlignmentFlag.AlignCenter, "MISSING")
            painter.end()

            icon = QIcon(canvas)
            self._thumb_cache[path] = icon
            return icon
        else:
            # Text entry icon
            cache_key = "_SYS_TEXT_ICON_"
            if cache_key in self._thumb_cache:
                return self._thumb_cache[cache_key]

            canvas = QPixmap(48, 48)
            canvas.fill(Qt.GlobalColor.transparent)
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor("#e0f2fe"))
            painter.setPen(QColor("#93c5fd"))
            painter.drawRoundedRect(1, 1, 46, 46, 4, 4)

            font = QFont("Segoe UI", 11, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor("#0284c7"))
            painter.drawText(QRect(0, 0, 48, 48), Qt.AlignmentFlag.AlignCenter, "TXT")
            painter.end()

            icon = QIcon(canvas)
            self._thumb_cache[cache_key] = icon
            return icon

    # -----------------------------------------------------------------
    # Live Preview Handling
    # -----------------------------------------------------------------
    def _on_selection_changed(self):
        """Updates the Live Preview panel whenever a row is selected."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._history):
            self.preview_stack.setCurrentIndex(2)
            self.preview_badge.setText("")
            return

        item = self._history[row]

        if item.ContentType == "Image":
            self.preview_stack.setCurrentIndex(0)
            self.preview_title.setText("🖼️ Image Preview")

            path = item.ImagePath or ""
            if path and os.path.exists(path):
                pm = QPixmap(path)
                if not pm.isNull():
                    # Scale for preview pane maintaining aspect ratio
                    avail_w = max(260, self.img_scroll.viewport().width() - 20)
                    avail_h = max(260, self.img_scroll.viewport().height() - 20)
                    scaled_pm = pm.scaled(avail_w, avail_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.lbl_image_preview.setPixmap(scaled_pm)

                    file_size_kb = os.path.getsize(path) / 1024.0
                    details = f"Dimensions: {pm.width()} × {pm.height()} px  •  Size: {file_size_kb:.1f} KB\nFile: {path}"
                    self.lbl_img_details.setText(details)
                    self.preview_badge.setText(f"{pm.width()}×{pm.height()} • {file_size_kb:.1f} KB")
                else:
                    self.lbl_image_preview.setText("Failed to decode image data.")
                    self.lbl_img_details.setText(f"File: {path}")
                    self.preview_badge.setText("Error")
            else:
                self.lbl_image_preview.setText("Image file does not exist on disk.")
                self.lbl_img_details.setText(f"File: {path}")
                self.preview_badge.setText("File not found")
        else:
            # Text Preview
            self.preview_stack.setCurrentIndex(1)
            self.preview_title.setText("📝 Text Preview")

            text = item.TextContent or ""
            self.txt_preview_edit.setPlainText(text)

            char_count = len(text)
            word_count = len(text.split())
            line_count = len(text.splitlines()) if text else 0
            stats = f"Length: {char_count} chars  •  Words: {word_count}  •  Lines: {line_count}"
            self.lbl_txt_details.setText(stats)
            self.preview_badge.setText(f"{char_count} chars • {word_count} words")

        # Clear previous status message
        self.lbl_status.setText("")

    # -----------------------------------------------------------------
    # Filtering and Search
    # -----------------------------------------------------------------
    def _on_filter_changed(self, index: int):
        self.load_data()

    def _on_search_changed(self, text: str):
        self.load_data()

    # -----------------------------------------------------------------
    # Copy and Action Handlers
    # -----------------------------------------------------------------
    def _get_selected_item(self) -> Optional[ClipboardHistory]:
        row = self.table.currentRow()
        if 0 <= row < len(self._history):
            return self._history[row]
        return None

    def _copy_selected_to_clipboard(self):
        """Copies the currently selected item (Image or Text) to the clipboard."""
        item = self._get_selected_item()
        if not item:
            return

        clipboard = QApplication.clipboard()
        if item.ContentType == "Image":
            if item.ImagePath and os.path.exists(item.ImagePath):
                pm = QPixmap(item.ImagePath)
                if not pm.isNull():
                    clipboard.setPixmap(pm)
                    self.lbl_status.setText("✅ Image copied to clipboard!")
                else:
                    QMessageBox.warning(self, "Error", "Failed to load image for clipboard.")
            else:
                QMessageBox.warning(self, "Error", "Image file not found on disk.")
        else:
            text = item.TextContent or ""
            clipboard.setText(text)
            self.lbl_status.setText("✅ Text copied to clipboard!")

    def _open_image_external(self):
        """Opens image in default system viewer."""
        item = self._get_selected_item()
        if item and item.ContentType == "Image" and item.ImagePath and os.path.exists(item.ImagePath):
            try:
                os.startfile(item.ImagePath)
            except Exception as e:
                logger.error(f"Error opening image: {e}")

    def _show_in_folder(self):
        """Reveals image file in Windows Explorer."""
        item = self._get_selected_item()
        if item and item.ContentType == "Image" and item.ImagePath and os.path.exists(item.ImagePath):
            try:
                subprocess.Popen(f'explorer /select,"{os.path.abspath(item.ImagePath)}"')
            except Exception as e:
                logger.error(f"Error showing in folder: {e}")

    def _save_as_note(self):
        """Saves selected clipboard entry into the Notes table."""
        item = self._get_selected_item()
        if not item:
            return

        if item.ContentType == "Text":
            text = item.TextContent or ""
            clean_title = text.strip().replace("\n", " ").replace("\r", "")
            if len(clean_title) > 35:
                clean_title = clean_title[:35] + "..."
            DataRepository.create_document(
                name=f"Clipboard: {clean_title}",
                desc=text,
                notes=text,
                category="PlainNotes",
                doc_type=2,
            )
            QMessageBox.information(self, "Saved", "Clipboard entry successfully saved to Notes!")
        else:
            filename = Path(item.ImagePath).name if item.ImagePath else "Captured Image"
            DataRepository.create_document(
                name=f"Image: {filename}",
                desc=f"Screenshot / image saved from clipboard.\nPath: {item.ImagePath}",
                notes=item.ImagePath or "",
                category="PlainNotes",
                doc_type=2,
            )
            QMessageBox.information(self, "Saved", "Image reference successfully saved to Notes!")

    def _delete_selected(self):
        """Deletes the selected clipboard item from database and table."""
        item = self._get_selected_item()
        if not item:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete this clipboard entry (ID {item.ID})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            success = DataRepository.delete_clipboard_entry(item.ID)
            if success:
                self.load_data()
                self.lbl_status.setText("🗑️ Entry deleted.")
