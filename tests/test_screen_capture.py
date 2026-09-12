"""
Unit tests for ScreenCaptureEngine and OverlayCanvas.
"""
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect, QPoint
from PyQt6.QtGui import QPixmap, QColor
from src.media.screen_capture import ScreenCaptureEngine
from src.media.overlay_canvas import OverlayCanvas, ToolMode, ArrowItem, RectItem

app = QApplication.instance() or QApplication(["test_screen"])


class TestScreenCapture(unittest.TestCase):

    def test_virtual_geometry(self):
        geom = ScreenCaptureEngine.get_virtual_geometry()
        self.assertGreater(geom.width(), 0)
        self.assertGreater(geom.height(), 0)
        print(f"Virtual desktop geometry: {geom.width()}x{geom.height()}")

    def test_save_and_copy(self):
        pixmap = QPixmap(200, 150)
        pixmap.fill(QColor(100, 150, 200))
        filepath = ScreenCaptureEngine.save_and_copy_screenshot(pixmap, filename_prefix="TestUnit")
        self.assertTrue(os.path.exists(filepath))
        # Clean up test file immediately so tests never leave orphaned screenshots
        if os.path.exists(filepath):
            os.remove(filepath)
        print(f"Screenshot successfully verified and cleaned up: {filepath}")

    def test_overlay_canvas_instantiation(self):
        canvas = OverlayCanvas()
        self.assertIsNotNone(canvas)
        self.assertEqual(canvas._current_tool, ToolMode.SELECT)
        print("OverlayCanvas instantiated successfully!")

    def test_overlay_escape_exit(self):
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import QEvent, Qt
        canvas = OverlayCanvas()
        canvas.start_capture()
        self.assertTrue(canvas.isVisible())

        # Simulate pressing Escape key
        esc_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        canvas.keyPressEvent(esc_event)

        self.assertFalse(canvas.isVisible())
        print("OverlayCanvas successfully dismissed on Escape key press!")

    def test_high_dpi_crop_and_finalize(self):
        from PIL import Image
        import numpy as np

        canvas = OverlayCanvas()
        dpr = 1.25
        mock_desktop = QPixmap(1920, 1080)
        mock_desktop.setDevicePixelRatio(dpr)
        mock_desktop.fill(QColor(100, 150, 200))
        canvas._desktop_pixmap = mock_desktop
        canvas._selection_rect = QRect(100, 100, 444, 408)

        # Trigger finalize and save
        canvas._finalize_and_save()

        # Find latest screenshot
        from src.config import SCREENSHOTS_DIR
        screenshots = sorted(SCREENSHOTS_DIR.glob("Screenshot_*.png"), key=os.path.getmtime)
        self.assertTrue(len(screenshots) > 0)
        latest = screenshots[-1]

        img = Image.open(latest)
        arr = np.array(img)
        # Expected physical dimensions: 444 * 1.25 = 555, 408 * 1.25 = 510
        self.assertEqual(img.size, (555, 510))

        # Check there are no unpainted black bands at the right or bottom edges
        rgb = arr[:, :, :3]
        is_black = (rgb == [0, 0, 0]).all(axis=-1)
        black_rows = np.where(is_black.all(axis=1))[0]
        black_cols = np.where(is_black.all(axis=0))[0]
        self.assertEqual(len(black_rows), 0, f"Found {len(black_rows)} unpainted black rows!")
        self.assertEqual(len(black_cols), 0, f"Found {len(black_cols)} unpainted black cols!")
        print(f"High-DPI screenshot verified successfully with size {img.size} and 0 black margins!")

    def test_text_annotation_entry_and_commit(self):
        from PyQt6.QtGui import QMouseEvent, QKeyEvent
        from PyQt6.QtCore import QEvent, Qt
        from src.media.overlay_canvas import TextItem

        canvas = OverlayCanvas()
        canvas.start_capture()
        canvas._selection_rect = QRect(50, 50, 500, 400)
        canvas._current_tool = ToolMode.TEXT

        # 1. Simulate mouse click inside selection to place text entry box
        from PyQt6.QtCore import QPointF
        click_pos = QPoint(120, 150)
        press_event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(120.0, 150.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        canvas.mousePressEvent(press_event)

        # 2. Verify inline text editor is visible and positioned
        self.assertTrue(canvas._text_editor.isVisible())
        self.assertEqual(canvas._text_editor.pos(), click_pos)

        # 3. Simulate typing text
        canvas._text_editor.setText("Bug report note")

        # 4. Simulate pressing Enter
        enter_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        canvas._text_editor.keyPressEvent(enter_event)

        # 5. Verify text is committed to annotations and editor is hidden
        self.assertFalse(canvas._text_editor.isVisible())
        self.assertEqual(len(canvas._annotations), 1)
        self.assertIsInstance(canvas._annotations[0], TextItem)
        self.assertEqual(canvas._annotations[0].text, "Bug report note")
        self.assertEqual(canvas._annotations[0].pos, click_pos)

        # 6. Test Escape cancels text entry without closing canvas
        canvas.mousePressEvent(press_event)
        self.assertTrue(canvas._text_editor.isVisible())
        esc_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        canvas._text_editor.keyPressEvent(esc_event)
        self.assertFalse(canvas._text_editor.isVisible())
        self.assertTrue(canvas.isVisible())  # Canvas still active!

        canvas.close()
        print("Text annotation entry and commit verified successfully!")


if __name__ == "__main__":
    unittest.main()
