"""
Unit tests for config_manager and path resolution in DigitalBrainEX AI.
"""
import os
import unittest
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect, QPoint

from src.utils.config_manager import (
    get_doc_folder,
    set_doc_folder,
    resolve_document_path,
)
from src.media.overlay_canvas import OverlayCanvas

app = QApplication.instance() or QApplication([])


class TestConfigManager(unittest.TestCase):

    def test_doc_folder_detection(self):
        doc_folder = get_doc_folder()
        self.assertIsNotNone(doc_folder)
        self.assertTrue(len(doc_folder) > 0)
        self.assertTrue(os.path.exists(doc_folder))

    def test_relative_path_resolution(self):
        # Test leading backslash relative path like \3\iEDX Firmware Design Doc v1p5.pdf
        rel_path = r"\3\iEDX Firmware Design Doc v1p5.pdf"
        resolved = resolve_document_path(rel_path)
        expected = os.path.normpath(os.path.join(get_doc_folder(), r"3\iEDX Firmware Design Doc v1p5.pdf"))
        self.assertEqual(resolved, expected)

    def test_forward_slash_relative_path(self):
        rel_path = "10/sample_file.txt"
        resolved = resolve_document_path(rel_path)
        expected = os.path.normpath(os.path.join(get_doc_folder(), r"10\sample_file.txt"))
        self.assertEqual(resolved, expected)

    def test_url_resolution(self):
        url = "https://github.com/project/repo"
        resolved = resolve_document_path(url)
        self.assertEqual(resolved, url)

    def test_empty_resolution(self):
        self.assertEqual(resolve_document_path(""), "")
        self.assertEqual(resolve_document_path(None), "")

    def test_multimonitor_toolbar_positioning(self):
        canvas = OverlayCanvas()
        # Simulate selection rectangle on a secondary monitor or virtual geometry
        canvas._selection_rect = QRect(100, 100, 300, 200)
        canvas._position_toolbar()
        # Ensure toolbar has moved to a valid non-empty position
        tb_pos = canvas.toolbar.pos()
        self.assertIsNotNone(tb_pos)
        self.assertTrue(canvas.toolbar.width() > 0)
        self.assertTrue(canvas.toolbar.height() > 0)
        canvas.close()


if __name__ == "__main__":
    unittest.main()
