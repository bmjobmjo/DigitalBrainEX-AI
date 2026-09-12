"""
Clipboard Monitor for DigitalBrainEX AI.
Tracks clipboard changes natively via PyQt6 QClipboard and stores history in SQLite.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QClipboard, QPixmap

from src.config import SCREENSHOTS_DIR
from src.core.repository import DataRepository
from src.core.event_bus import event_bus, EVT_CLIPBOARD_NEW
from src.core.logger import logger


class ClipboardMonitor(QObject):
    clipboard_updated = pyqtSignal(str)  # (content_type)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_text = ""
        self._is_monitoring = False
        self._clipboard: Optional[QClipboard] = None

    def start_monitoring(self):
        """Attaches clipboard listener to QApplication clipboard."""
        if self._is_monitoring:
            return

        app = QApplication.instance()
        if not app:
            logger.warning("No QApplication instance available for clipboard monitoring.")
            return

        self._clipboard = app.clipboard()
        self._clipboard.dataChanged.connect(self._on_clipboard_changed)
        self._is_monitoring = True
        logger.info("Clipboard monitor started.")

    def stop_monitoring(self):
        if self._is_monitoring and self._clipboard:
            try:
                self._clipboard.dataChanged.disconnect(self._on_clipboard_changed)
            except Exception:
                pass
            self._is_monitoring = False
            logger.info("Clipboard monitor stopped.")

    def _on_clipboard_changed(self):
        if not self._is_monitoring or not self._clipboard:
            return

        # 1. Check for text
        text = self._clipboard.text()
        if text and text.strip():
            # Avoid duplicate recordings of identical recent clipboard text
            if text == self._last_text:
                return
            self._last_text = text

            try:
                DataRepository.add_clipboard_entry(
                    content_type="Text",
                    text_content=text,
                    image_path=None,
                )
                logger.debug(f"Saved text to clipboard history: {text[:30]}...")
                event_bus.publish(EVT_CLIPBOARD_NEW, content_type="Text", text=text)
                self.clipboard_updated.emit("Text")
            except Exception as e:
                logger.error(f"Failed to record clipboard text: {e}")
            return

        # 2. Check for image
        pixmap = self._clipboard.pixmap()
        if not pixmap.isNull() and pixmap.width() > 10 and pixmap.height() > 10:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ClipImage_{timestamp}.png"
            filepath = str(SCREENSHOTS_DIR / filename)

            try:
                pixmap.save(filepath, "PNG")
                DataRepository.add_clipboard_entry(
                    content_type="Image",
                    text_content=None,
                    image_path=filepath,
                )
                logger.debug(f"Saved image to clipboard history: {filepath}")
                event_bus.publish(EVT_CLIPBOARD_NEW, content_type="Image", path=filepath)
                self.clipboard_updated.emit("Image")
            except Exception as e:
                logger.error(f"Failed to save clipboard image: {e}")
