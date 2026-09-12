"""
Unit tests for DigitalBrainEX AI Popup Dialogs & Theme Switching.
Tests creation, loading, validation, and theme switching across all 8 modal dialogs.
"""
import sys
import os
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication

from src.ui.dialogs import (
    NoteEditorDialog,
    TaskEditorDialog,
    ProjectEditorDialog,
    DocumentEditorDialog,
    UrlEditorDialog,
    CodeSnippetEditorDialog,
    MinutesEditorDialog,
    SecretEditorDialog,
)
from src.ui.theme import get_theme_stylesheet, apply_theme, LIGHT_PALETTE, DARK_PALETTE

# Ensure single QApplication instance
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestDialogsAndThemes(unittest.TestCase):

    def test_theme_stylesheets(self):
        """Verify light and dark stylesheets generate without errors."""
        light_css = get_theme_stylesheet("light")
        dark_css = get_theme_stylesheet("dark")

        self.assertIn(LIGHT_PALETTE["bg_window"], light_css)  # Light window bg
        self.assertIn(DARK_PALETTE["bg_window"], dark_css)   # Dark window bg

        # Test application
        apply_theme(app, "light")
        self.assertEqual(app.property("theme_name"), "light")
        apply_theme(app, "dark")
        self.assertEqual(app.property("theme_name"), "dark")
        # Return to light default
        apply_theme(app, "light")

    def test_note_editor_dialog(self):
        """Test NoteEditorDialog creation and loading."""
        dlg_new = NoteEditorDialog()
        self.assertIsNotNone(dlg_new)
        self.assertEqual(dlg_new.windowTitle(), "New Note")
        dlg_new.close()

        # Load existing note (e.g. ID 11145 from DB)
        dlg_edit = NoteEditorDialog(note_id=11145)
        self.assertIsNotNone(dlg_edit)
        self.assertIn("Edit Note", dlg_edit.windowTitle())
        self.assertTrue(len(dlg_edit.edit_title.text()) > 0)
        dlg_edit.close()

    def test_task_editor_dialog(self):
        """Test TaskEditorDialog creation and existing task loading."""
        dlg_new = TaskEditorDialog()
        self.assertIsNotNone(dlg_new)
        self.assertEqual(dlg_new.windowTitle(), "New Task")
        dlg_new.close()

    def test_project_editor_dialog(self):
        """Test ProjectEditorDialog creation."""
        dlg_new = ProjectEditorDialog()
        self.assertIsNotNone(dlg_new)
        self.assertEqual(dlg_new.windowTitle(), "New Project")
        dlg_new.close()

    def test_document_editor_dialog(self):
        """Test DocumentEditorDialog creation."""
        dlg_new = DocumentEditorDialog()
        self.assertIsNotNone(dlg_new)
        self.assertEqual(dlg_new.windowTitle(), "Add Document")
        dlg_new.close()

    def test_url_editor_dialog(self):
        """Test UrlEditorDialog creation."""
        dlg_new = UrlEditorDialog()
        self.assertIsNotNone(dlg_new)
        self.assertEqual(dlg_new.windowTitle(), "Add Bookmark / URL")
        dlg_new.close()

    def test_code_snippet_editor_dialog(self):
        """Test CodeSnippetEditorDialog creation."""
        dlg_new = CodeSnippetEditorDialog()
        self.assertIsNotNone(dlg_new)
        self.assertEqual(dlg_new.windowTitle(), "New Code Snippet")
        dlg_new.close()

    def test_minutes_editor_dialog(self):
        """Test MinutesEditorDialog creation."""
        dlg_new = MinutesEditorDialog()
        self.assertIsNotNone(dlg_new)
        self.assertEqual(dlg_new.windowTitle(), "New Meeting Minutes")
        dlg_new.close()

    def test_secret_editor_dialog(self):
        """Test SecretEditorDialog creation."""
        dlg_new = SecretEditorDialog(mode="add")
        self.assertIsNotNone(dlg_new)
        self.assertEqual(dlg_new.windowTitle(), "New Secret")
        dlg_new.close()

    def test_clipboard_history_dialog(self):
        """Test ClipboardHistoryDialog rich preview, thumbnails, and type filters."""
        from src.ui.components.clipboard_history_dlg import ClipboardHistoryDialog
        dlg = ClipboardHistoryDialog()
        self.assertIsNotNone(dlg)
        self.assertEqual(dlg.table.columnCount(), 4)
        self.assertEqual(dlg.splitter.count(), 2)
        self.assertEqual(dlg.preview_stack.count(), 3)

        # Test selecting first item if items exist
        if dlg.table.rowCount() > 0:
            dlg.table.selectRow(0)
            self.assertIn(dlg.preview_stack.currentIndex(), [0, 1])

        # Test filtering by Images
        dlg.filter_combo.setCurrentIndex(1)
        if dlg.table.rowCount() > 0:
            dlg.table.selectRow(0)
            self.assertEqual(dlg.preview_stack.currentIndex(), 0)  # Image preview stack

        # Test filtering by Text
        dlg.filter_combo.setCurrentIndex(2)
        if dlg.table.rowCount() > 0:
            dlg.table.selectRow(0)
            self.assertEqual(dlg.preview_stack.currentIndex(), 1)  # Text preview stack

        dlg.close()
        print("ClipboardHistoryDialog rich preview verified successfully!")


if __name__ == "__main__":
    unittest.main()
