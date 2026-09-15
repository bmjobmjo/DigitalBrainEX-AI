"""
Navigation Sidebar for DigitalBrainEX AI.
Provides clean, modern navigation across the 12 functional modules.
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QFrame,
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QFont, QIcon
from src.ui.icons import IconHelper


class SidebarWidget(QWidget):
    module_changed = pyqtSignal(int, str)  # (module_index, module_name)

    MODULES = [
        ("Projects", "Projects", "Projects"),
        ("Tasks", "Tasks", "Tasks"),
        ("Documents", "Documents", "Documents"),
        ("URLs", "URLs", "URLs"),
        ("Code Snippets", "Code Snippets", "Code Snippets"),
        ("Minutes", "Minutes", "Meeting Minutes"),
        ("File Manager", "FileManager", "File Manager"),
        ("Notes", "Notes", "Notes"),
        ("Secrets", "Secrets", "Secrets"),
        ("TrackMe", "TrackMe", "TrackMe"),
        ("Ask Me", "AskMe", "Ask Me"),
        ("Settings", "Settings", "Settings"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(4)

        # Navigation Header
        nav_label = QLabel("MODULES")
        nav_label.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 700; padding-left: 8px;")
        layout.addWidget(nav_label)

        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("SidebarList")
        self.list_widget.setIconSize(QSize(20, 20))

        for idx, (label, tag, _) in enumerate(self.MODULES):
            item = QListWidgetItem(label)
            icon = IconHelper.get_icon(tag)
            item.setIcon(icon)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            item.setData(Qt.ItemDataRole.UserRole + 1, tag)
            self.list_widget.addItem(item)

        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self.list_widget)

        # Select first item by default
        self.list_widget.setCurrentRow(1)  # Default to Tasks & Reminders (like original app)

    def _on_row_changed(self, row: int):
        if 0 <= row < len(self.MODULES):
            _, tag, _ = self.MODULES[row]
            self.module_changed.emit(row, tag)

    def get_module_title(self, row: int) -> str:
        if 0 <= row < len(self.MODULES):
            return self.MODULES[row][2]
        return ""

    def select_module_by_name(self, name: str):
        for row, (_, tag, _) in enumerate(self.MODULES):
            if tag.lower() == name.lower():
                self.list_widget.setCurrentRow(row)
                break

    def set_current_module(self, module):
        """Selects a module by its integer index or string tag/name."""
        if isinstance(module, int):
            if 0 <= module < len(self.MODULES):
                self.list_widget.setCurrentRow(module)
        elif isinstance(module, str):
            self.select_module_by_name(module)
