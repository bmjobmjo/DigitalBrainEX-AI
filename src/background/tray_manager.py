"""
System Tray Manager for DigitalBrainEX AI.
Provides persistent background tray icon, quick actions menu, and notification dispatching.
"""
from PyQt6.QtWidgets import (
    QSystemTrayIcon,
    QMenu,
    QApplication,
)
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QFont
from PyQt6.QtCore import pyqtSignal, QObject
from src.core.logger import logger


class TrayManager(QObject):
    show_main_window_requested = pyqtSignal()
    screenshot_requested = pyqtSignal()
    clipboard_history_requested = pyqtSignal()
    record_meeting_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    exit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon = QSystemTrayIcon(parent)
        self._default_icon = None
        self._is_blinking = False
        self._blink_state = False
        self._blink_counter = 0
        self._current_alert_type = None

        from PyQt6.QtCore import QTimer
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(500)
        self._blink_timer.timeout.connect(self._toggle_blink)

        self._init_icon()
        self._init_menu()
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _generate_default_icon(self) -> QIcon:
        """Generates a stylish 32x32 digital brain icon pixmap if no file icon exists."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background rounded badge
        painter.setBrush(QColor("#2563eb"))
        painter.setPen(QColor("#1d4ed8"))
        painter.drawRoundedRect(2, 2, 28, 28, 6, 6)

        # Text "DB"
        painter.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), 0x0084, "DB")  # AlignCenter
        painter.end()

        return QIcon(pixmap)

    def _init_icon(self):
        import os
        from src.ui.icons import IconHelper
        from src.config import ASSETS_DIR
        icon_path = str(ASSETS_DIR / "tray_icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "tray_icon.ico"))
        if os.path.exists(icon_path):
            self._default_icon = QIcon(icon_path)
        else:
            self._default_icon = self._generate_default_icon()

        self._water_icon = IconHelper.get_icon("water_drop", 32)
        self._sedentary_icon = IconHelper.get_icon("sedentary_walk", 32)

        self.tray_icon.setIcon(self._default_icon)
        self.tray_icon.setToolTip("DigitalBrainEX AI - Companion & Task Diary")

    def start_blinking(self, alert_type: str):
        """Starts blinking the tray icon with the appropriate wellness icon."""
        self._current_alert_type = alert_type
        self._is_blinking = True
        self._blink_counter = 0
        self._blink_state = True

        if alert_type == "water":
            self.tray_icon.setIcon(self._water_icon)
            self.tray_icon.setToolTip("DigitalBrainEX AI - 💧 Time to Drink Water!")
        else:
            self.tray_icon.setIcon(self._sedentary_icon)
            self.tray_icon.setToolTip("DigitalBrainEX AI - 🚶 Time to Stand & Stretch!")

        self._blink_timer.start()

    def stop_blinking(self):
        """Stops tray icon blinking and restores standard icon and tooltip."""
        if not self._is_blinking:
            return
        self._is_blinking = False
        self._blink_timer.stop()
        self.tray_icon.setIcon(self._default_icon)
        self.tray_icon.setToolTip("DigitalBrainEX AI - Companion & Task Diary")

    def _toggle_blink(self):
        self._blink_state = not self._blink_state
        self._blink_counter += 1

        # Automatically stop blinking after 60 ticks (30 seconds)
        if self._blink_counter > 60:
            self.stop_blinking()
            return

        if self._blink_state:
            if self._current_alert_type == "water":
                self.tray_icon.setIcon(self._water_icon)
            else:
                self.tray_icon.setIcon(self._sedentary_icon)
        else:
            self.tray_icon.setIcon(self._default_icon)

    def _init_menu(self):
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu { background-color: #ffffff; color: #1e293b; border: 1px solid #c8ccd1; padding: 4px; border-radius: 6px; } "
            "QMenu::item { padding: 6px 18px; border-radius: 4px; } "
            "QMenu::item:selected { background-color: #2563eb; color: #ffffff; font-weight: bold; } "
            "QMenu::separator { height: 1px; background-color: #e2e8f0; margin: 4px 8px; }"
        )

        action_open = menu.addAction("Open DigitalBrainEX AI")
        font = action_open.font()
        font.setBold(True)
        action_open.setFont(font)
        action_open.triggered.connect(self.show_main_window_requested.emit)

        menu.addSeparator()

        action_screenshot = menu.addAction("📸 Take Screenshot (Ctrl+P)")
        action_screenshot.triggered.connect(self.screenshot_requested.emit)

        action_clipboard = menu.addAction("📋 Clipboard History (Ctrl+H)")
        action_clipboard.triggered.connect(self.clipboard_history_requested.emit)

        action_record = menu.addAction("🎙️ Record Meeting Audio")
        action_record.triggered.connect(self.record_meeting_requested.emit)

        menu.addSeparator()

        action_settings = menu.addAction("⚙️ Settings")
        action_settings.triggered.connect(self.settings_requested.emit)

        menu.addSeparator()

        action_exit = menu.addAction("❌ Exit Application")
        action_exit.triggered.connect(self.exit_requested.emit)

        self.tray_icon.setContextMenu(menu)

    def show(self):
        """Displays the tray icon."""
        self.tray_icon.show()

    def hide(self):
        """Hides the tray icon."""
        self.tray_icon.hide()

    def show_notification(
        self,
        title: str,
        message: str,
        icon_type: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        msecs: int = 4000,
    ):
        """Shows a native Windows system tray balloon notification."""
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, icon_type, msecs)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        self.stop_blinking()
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_main_window_requested.emit()
