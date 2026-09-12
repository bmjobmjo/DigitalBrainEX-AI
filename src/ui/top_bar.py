"""
Top Bar Widget for DigitalBrainEX AI.
Houses project selector, global search, quick action buttons, and service status badges.
"""
import os
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QLineEdit,
    QFrame,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap
from src.core.repository import DataRepository
from src.core.event_bus import event_bus, EVT_PROJECT_CHANGED
from src.ui.icons import IconHelper
from src.core.logger import logger


class TopBarWidget(QFrame):
    project_changed = pyqtSignal(int, str)  # (project_id, project_name)
    search_requested = pyqtSignal(str)
    screenshot_requested = pyqtSignal()
    clipboard_requested = pyqtSignal()
    record_audio_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopBarWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(58)
        self._init_ui()
        self.load_projects()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 12, 6)
        layout.setSpacing(10)

        # 1. Authentic App Logo from original C# resources
        self.logo_label = QLabel()
        self.logo_label.setObjectName("TopBarLogoLabel")
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png"))
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            self.logo_label.setPixmap(pix.scaled(140, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.logo_label)

        layout.addStretch(1)

        # 2. Centered Active Module Title
        self.module_title = QLabel("Projects")
        self.module_title.setObjectName("TopBarModuleTitle")
        self.module_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.module_title)

        layout.addStretch(1)

        # 3. Project Selector
        proj_label = QLabel("Select Project:")
        proj_label.setObjectName("TopBarProjText")
        layout.addWidget(proj_label)

        self.combo_project = QComboBox()
        self.combo_project.setMinimumWidth(170)
        self.combo_project.currentIndexChanged.connect(self._on_project_combo_changed)
        layout.addWidget(self.combo_project)

        self.btn_clear_project = QPushButton("Clear")
        self.btn_clear_project.setIcon(IconHelper.get_icon("clear", 14))
        self.btn_clear_project.setToolTip("View entries across all projects")
        self.btn_clear_project.clicked.connect(self._clear_project_filter)
        layout.addWidget(self.btn_clear_project)

        # 4. Global Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setFixedWidth(150)
        self.search_input.returnPressed.connect(self._on_search_submitted)
        layout.addWidget(self.search_input)

        # 5. Quick Actions (Standard Desktop Buttons)
        self.btn_screenshot = QPushButton("Screenshot")
        self.btn_screenshot.setIcon(IconHelper.get_icon("screenshot", 16))
        self.btn_screenshot.setToolTip("Capture Screen or Region (Ctrl+P)")
        self.btn_screenshot.clicked.connect(self.screenshot_requested.emit)
        layout.addWidget(self.btn_screenshot)

        self.btn_clipboard = QPushButton("Clipboard")
        self.btn_clipboard.setIcon(IconHelper.get_icon("copy", 16))
        self.btn_clipboard.setToolTip("Open Clipboard History (Ctrl+H)")
        self.btn_clipboard.clicked.connect(self.clipboard_requested.emit)
        layout.addWidget(self.btn_clipboard)

        self.btn_record = QPushButton("Record")
        self.btn_record.setIcon(IconHelper.get_icon("mic", 16))
        self.btn_record.setToolTip("Start Meeting Audio Recording")
        self.btn_record.clicked.connect(self.record_audio_requested.emit)
        layout.addWidget(self.btn_record)

        # Active Status Indicator
        self.status_indicator = QLabel("● Active")
        self.status_indicator.setStyleSheet("color: #d1fae5; font-size: 11px; font-weight: bold;")
        self.status_indicator.setToolTip("Background Tracking & Listeners Active")
        layout.addWidget(self.status_indicator)

    def set_module_title(self, title: str):
        """Updates the active module title displayed in the top bar center."""
        self.module_title.setText(title)

    def load_projects(self):
        """Loads projects from DB into the selector combo box."""
        self.combo_project.blockSignals(True)
        self.combo_project.clear()
        self.combo_project.addItem("All Projects", userData=0)

        try:
            projects = DataRepository.get_all_projects(status="Active")
            for p in projects:
                name = p.ProjectName.strip() if p.ProjectName else f"Project #{p.PojectID}"
                self.combo_project.addItem(name, userData=p.PojectID)
        except Exception as e:
            logger.error(f"Failed to load projects into top bar: {e}")
        finally:
            self.combo_project.blockSignals(False)

    def _on_project_combo_changed(self, index: int):
        proj_id = self.combo_project.currentData() or 0
        proj_name = self.combo_project.currentText()
        event_bus.publish(EVT_PROJECT_CHANGED, project_id=proj_id, project_name=proj_name)
        self.project_changed.emit(proj_id, proj_name)

    def _clear_project_filter(self):
        self.combo_project.setCurrentIndex(0)

    def _on_search_submitted(self):
        query = self.search_input.text().strip()
        self.search_requested.emit(query)

    def get_current_project_id(self) -> int:
        return self.combo_project.currentData() or 0

    def get_current_project_name(self) -> str:
        return self.combo_project.currentText()
