"""
Global Hotkey Manager for DigitalBrainEX AI.
Listens for system-wide shortcuts (e.g. PrintScreen, Ctrl+P) even when minimized.
"""
from typing import Callable, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from src.core.logger import logger

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


class GlobalHotkeyManager(QObject):
    screenshot_triggered = pyqtSignal()
    clipboard_triggered = pyqtSignal()
    escape_triggered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_registered = False

    def register_hotkeys(self):
        if not KEYBOARD_AVAILABLE or self._is_registered:
            return

        try:
            # Register PrintScreen
            keyboard.add_hotkey("print screen", lambda: self.screenshot_triggered.emit(), suppress=False)
            # Register Ctrl+P
            keyboard.add_hotkey("ctrl+shift+p", lambda: self.screenshot_triggered.emit(), suppress=False)
            # Register Ctrl+H
            keyboard.add_hotkey("ctrl+shift+h", lambda: self.clipboard_triggered.emit(), suppress=False)
            # Register Esc (for emergency capture dismiss)
            keyboard.add_hotkey("esc", lambda: self.escape_triggered.emit(), suppress=False)

            self._is_registered = True
            logger.info("Global hotkeys registered (PrintScreen, Ctrl+Shift+P, Ctrl+Shift+H, Esc).")
        except Exception as e:
            logger.warning(f"Could not register global hotkeys: {e}")

    def unregister_hotkeys(self):
        if not KEYBOARD_AVAILABLE or not self._is_registered:
            return
        try:
            keyboard.unhook_all_hotkeys()
            self._is_registered = False
            logger.info("Global hotkeys unregistered.")
        except Exception as e:
            logger.warning(f"Error unregistering global hotkeys: {e}")
