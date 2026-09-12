"""
Screen Capture Engine for DigitalBrainEX AI.
Captures desktop screens, individual monitor geometries, and handles image persistence.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QScreen, QImage, QPainter, QColor
from PyQt6.QtCore import QRect, QPoint, Qt
from src.config import SCREENSHOTS_DIR
from src.core.repository import DataRepository
from src.core.event_bus import event_bus, EVT_SCREENSHOT_TAKEN
from src.core.logger import logger


class ScreenCaptureEngine:
    """Captures screens, virtual multi-monitor geometry, and saves screenshot files."""

    @staticmethod
    def get_virtual_geometry() -> QRect:
        """Returns the union bounding rectangle of all attached monitors."""
        screens = QApplication.screens()
        if not screens:
            return QRect(0, 0, 1920, 1080)

        virtual_rect = screens[0].geometry()
        for s in screens[1:]:
            virtual_rect = virtual_rect.united(s.geometry())
        return virtual_rect

    @staticmethod
    def capture_full_virtual_desktop() -> QPixmap:
        """
        Captures the entire virtual desktop across all connected screens.
        Composites each screen's buffer onto a unified high-res pixmap.
        """
        screens = QApplication.screens()
        if not screens:
            return QPixmap()

        if len(screens) == 1:
            return screens[0].grabWindow(0)

        virtual_rect = ScreenCaptureEngine.get_virtual_geometry()
        max_dpr = max((s.devicePixelRatio() for s in screens), default=1.0)
        phys_w = max(1, int(round(virtual_rect.width() * max_dpr)))
        phys_h = max(1, int(round(virtual_rect.height() * max_dpr)))

        composite_pixmap = QPixmap(phys_w, phys_h)
        composite_pixmap.setDevicePixelRatio(max_dpr)
        composite_pixmap.fill(QColor(0, 0, 0))

        painter = QPainter(composite_pixmap)
        for s in screens:
            screen_pixmap = s.grabWindow(0)
            # Offset position relative to virtual desktop top-left
            offset_x = s.geometry().x() - virtual_rect.x()
            offset_y = s.geometry().y() - virtual_rect.y()
            painter.drawPixmap(offset_x, offset_y, screen_pixmap)
        painter.end()

        return composite_pixmap

    @staticmethod
    def capture_region(pixmap: QPixmap, region: QRect) -> QPixmap:
        """Crops a pixmap to the given region in logical coordinates."""
        dpr = pixmap.devicePixelRatio()
        if dpr <= 0:
            dpr = 1.0

        phys_rect = QRect(
            int(round(region.x() * dpr)),
            int(round(region.y() * dpr)),
            int(round(region.width() * dpr)),
            int(round(region.height() * dpr)),
        )
        # Ensure region is within bounds of pixmap physical device dimensions
        bounds = QRect(0, 0, pixmap.width(), pixmap.height())
        intersected = phys_rect.intersected(bounds)
        if intersected.isEmpty():
            return pixmap
        cropped = pixmap.copy(intersected)
        cropped.setDevicePixelRatio(dpr)
        return cropped

    @staticmethod
    def save_and_copy_screenshot(
        pixmap: QPixmap,
        filename_prefix: str = "Screenshot",
        copy_to_clipboard: bool = True,
    ) -> str:
        """
        Saves screenshot to SCREENSHOTS_DIR and copies it to Windows clipboard.
        Also records entry into ClipboardHistory database table.
        Returns the saved file path.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.png"
        filepath = str(SCREENSHOTS_DIR / filename)

        # Save to disk
        pixmap.save(filepath, "PNG")
        logger.info(f"Screenshot saved to: {filepath}")

        # Copy to Windows clipboard
        if copy_to_clipboard:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)

        # Record in ClipboardHistory table
        try:
            DataRepository.add_clipboard_entry(
                content_type="Image",
                text_content=None,
                image_path=filepath,
            )
        except Exception as e:
            logger.error(f"Failed to record screenshot in clipboard history: {e}")

        # Publish event
        event_bus.publish(EVT_SCREENSHOT_TAKEN, file_path=filepath)

        return filepath
