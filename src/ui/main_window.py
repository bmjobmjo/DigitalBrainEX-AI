"""
Main Application Window for DigitalBrainEX AI.
Assembles the TopBar, Sidebar, View Stack, and integrates System Tray and Global Hotkeys.
"""
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QApplication,
    QMessageBox,
    QLabel,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QKeyCombination
from PyQt6.QtGui import QKeySequence, QShortcut, QCloseEvent

from src.config import APP_NAME, APP_VERSION
from src.ui.top_bar import TopBarWidget
from src.ui.sidebar import SidebarWidget
from src.ui.components.clipboard_history_dlg import ClipboardHistoryDialog
from src.ui.components.notification_blinker import NotificationBlinker

# Views
from src.ui.views.projects_view import ProjectsView
from src.ui.views.tasks_view import TasksView
from src.ui.views.documents_view import DocumentsView
from src.ui.views.urls_view import UrlsView
from src.ui.views.code_snippets_view import CodeSnippetsView
from src.ui.views.minutes_view import MinutesView
from src.ui.views.file_manager_view import FileManagerView
from src.ui.views.notes_view import NotesView
from src.ui.views.secrets_view import SecretsView
from src.ui.views.trackme_view import TrackMeView
from src.ui.views.ask_me_view import AskMeView
from src.ui.views.settings_view import SettingsView

from src.media.overlay_canvas import OverlayCanvas
from src.core.logger import logger


class MainWindow(QMainWindow):
    trigger_screenshot = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - v{APP_VERSION}")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)

        import os
        from PyQt6.QtGui import QIcon
        from src.utils.win32_helper import setup_windows_app_id, apply_native_window_icon
        setup_windows_app_id()
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "app_icon.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._minimize_to_tray_on_close = True
        self._init_ui()
        self._setup_shortcuts()

    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        central_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Bar
        self.top_bar = TopBarWidget(self)
        self.top_bar.screenshot_requested.connect(self._on_screenshot_requested)
        self.top_bar.clipboard_requested.connect(self._open_clipboard_history)
        self.top_bar.record_audio_requested.connect(self._on_record_audio_requested)
        root_layout.addWidget(self.top_bar)

        # 2. Main Content Body (Sidebar + View Stack)
        body_widget = QWidget()
        body_widget.setObjectName("BodyWidget")
        body_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left Sidebar
        self.sidebar = SidebarWidget(self)
        self.sidebar.module_changed.connect(self._on_module_changed)
        body_layout.addWidget(self.sidebar)

        # Right View Stack
        self.view_stack = QStackedWidget()
        self.view_stack.setObjectName("ViewStack")
        self.view_stack.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Instantiate all 12 views
        self.view_projects = ProjectsView()
        self.view_tasks = TasksView()
        self.view_documents = DocumentsView()
        self.view_urls = UrlsView()
        self.view_snippets = CodeSnippetsView()
        self.view_minutes = MinutesView()
        self.view_file_manager = FileManagerView()
        self.view_notes = NotesView()
        self.view_secrets = SecretsView()
        self.view_trackme = TrackMeView()
        self.view_ask_me = AskMeView()
        self.view_settings = SettingsView()

        # Wire cross-view updates
        self.view_projects.project_updated.connect(self.top_bar.load_projects)
        self.top_bar.search_requested.connect(self._on_top_bar_search)

        # Wire AskMe AI Agent
        from src.ai.agents import AskMeAgent
        self.ask_me_agent = AskMeAgent(self)
        self.view_ask_me.send_message_requested.connect(self.ask_me_agent.query)
        self.view_ask_me.open_settings_requested.connect(self._open_settings_for_genai)

        # Add to stack in index order matching SidebarWidget.MODULES
        self.view_stack.addWidget(self.view_projects)       # 0: Projects
        self.view_stack.addWidget(self.view_tasks)          # 1: Tasks
        self.view_stack.addWidget(self.view_documents)      # 2: Documents
        self.view_stack.addWidget(self.view_urls)           # 3: URLs
        self.view_stack.addWidget(self.view_snippets)       # 4: Code Snippets
        self.view_stack.addWidget(self.view_minutes)        # 5: Minutes
        self.view_stack.addWidget(self.view_file_manager)   # 6: File Manager
        self.view_stack.addWidget(self.view_notes)          # 7: Notes
        self.view_stack.addWidget(self.view_secrets)        # 8: Secrets
        self.view_stack.addWidget(self.view_trackme)        # 9: TrackMe
        self.view_stack.addWidget(self.view_ask_me)         # 10: Ask Me
        self.view_stack.addWidget(self.view_settings)       # 11: Settings

        body_layout.addWidget(self.view_stack)
        root_layout.addWidget(body_widget)

        # 3. Bottom Slate Gray Status Banner (matches reference screenshots)
        footer = QFrame()
        footer.setObjectName("FooterBanner")
        footer.setFixedHeight(44)
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(0, 3, 0, 3)
        footer_layout.setSpacing(1)

        lbl_brand = QLabel("DIGITAL BRAIN")
        lbl_brand.setObjectName("FooterBrandLabel")
        lbl_brand.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_ver = QLabel(f"v{APP_VERSION} AI Edition")
        lbl_ver.setObjectName("FooterVersionLabel")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)

        footer_layout.addWidget(lbl_brand)
        footer_layout.addWidget(lbl_ver)
        root_layout.addWidget(footer)

        # Notification Blinker component
        self.blinker = NotificationBlinker(self)
        self.blinker.clicked.connect(self._on_blinker_clicked)

        # Transparent Screenshot Overlay Canvas
        self.overlay_canvas = OverlayCanvas()

        # Default to Tasks View (index 1)
        self.view_stack.setCurrentIndex(1)
        self.top_bar.set_module_title(self.sidebar.get_module_title(1))

    def _setup_shortcuts(self):
        """Sets up application-wide keyboard shortcuts."""
        # Screenshot shortcut: Ctrl+P
        self.shortcut_screenshot = QShortcut(QKeySequence("Ctrl+P"), self)
        self.shortcut_screenshot.activated.connect(self._on_screenshot_requested)

        # Clipboard history shortcut: Ctrl+H
        self.shortcut_clipboard = QShortcut(QKeySequence("Ctrl+H"), self)
        self.shortcut_clipboard.activated.connect(self._open_clipboard_history)

    def _on_module_changed(self, index: int, tag: str):
        if 0 <= index < self.view_stack.count():
            self.view_stack.setCurrentIndex(index)
            title = self.sidebar.get_module_title(index)
            if title:
                self.top_bar.set_module_title(title)
            # Trigger load/refresh for the active view
            active_widget = self.view_stack.widget(index)
            if hasattr(active_widget, "load_data"):
                active_widget.load_data()
            if hasattr(active_widget, "refresh_configuration_state"):
                active_widget.refresh_configuration_state()
            if hasattr(active_widget, "on_enter_screen"):
                active_widget.on_enter_screen()

    def _on_top_bar_search(self, query: str):
        active_view = self.view_stack.currentWidget()
        if not active_view:
            return
        if hasattr(active_view, "search_input"):
            active_view.search_input.setText(query)
            for fn_name in (
                "_filter_docs",
                "_filter_tasks",
                "_filter_snippets",
                "_filter_notes",
                "_filter_secrets",
                "_filter_urls",
                "_filter_projects",
                "_filter_minutes",
            ):
                if hasattr(active_view, fn_name):
                    getattr(active_view, fn_name)()
                    break



    def _on_screenshot_requested(self):
        if hasattr(self, "overlay_canvas") and self.overlay_canvas.isVisible():
            self.overlay_canvas.close()
            return
        self.overlay_canvas.start_capture()
        self.trigger_screenshot.emit()

    def _on_escape_pressed(self):
        if hasattr(self, "overlay_canvas") and self.overlay_canvas.isVisible():
            self.overlay_canvas.close()

    def _open_clipboard_history(self):
        dlg = ClipboardHistoryDialog(self)
        dlg.exec()

    def _on_record_audio_requested(self):
        # Switch to Minutes view
        self.sidebar.select_module_by_name("Minutes")

    def _on_blinker_clicked(self):
        self.show_and_activate()
        self.sidebar.select_module_by_name("Tasks")

    def _open_settings_for_genai(self):
        """Navigates to Settings and activates the GenAI & LLM tab."""
        self.sidebar.set_current_module(11)
        self._on_module_changed(11, "Settings")
        if hasattr(self, "view_settings") and hasattr(self.view_settings, "tabs"):
            self.view_settings.tabs.setCurrentIndex(2)

    def show_and_activate(self):
        """Restores window from tray or minimized state and brings to foreground."""
        import sys
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()

        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.raise_()
        self.activateWindow()

        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                # SW_RESTORE = 9
                ctypes.windll.user32.ShowWindow(hwnd, 9)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass

        import os
        from src.utils.win32_helper import apply_native_window_icon
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "app_icon.ico"))
        if os.path.exists(icon_path):
            apply_native_window_icon(int(self.winId()), icon_path)

    def trigger_task_alert(self, title: str, message: str):
        """Flashes the screen border to alert user of imminent task deadline."""
        self.blinker.start_blink()

    def closeEvent(self, event: QCloseEvent):
        """Minimizes to tray if configured, otherwise exits."""
        if self._minimize_to_tray_on_close:
            event.ignore()
            self.hide()
        else:
            event.accept()
