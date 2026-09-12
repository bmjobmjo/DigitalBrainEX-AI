"""
Tests for IconHelper, Windows Startup Manager, and Setup Wizard.
"""
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from src.ui.icons import IconHelper, SVG_ICONS
from src.utils.startup_manager import (
    is_auto_startup_enabled,
    set_auto_startup,
    get_default_launch_command,
)
from src.installer.setup_gui import SetupWizard

app = QApplication.instance() or QApplication(["test_icons"])


class TestIconsAndInstaller(unittest.TestCase):

    def test_all_svg_icons(self):
        """Verifies every defined icon renders a valid pixmap and icon."""
        for icon_name in SVG_ICONS.keys():
            pm = IconHelper.get_pixmap(icon_name, 24)
            self.assertFalse(pm.isNull(), f"Pixmap for {icon_name} should not be null")
            self.assertEqual(pm.width(), 24)
            self.assertEqual(pm.height(), 24)

            icon = IconHelper.get_icon(icon_name)
            self.assertFalse(icon.isNull(), f"QIcon for {icon_name} should not be null")

    def test_startup_manager_registry(self):
        """Verifies auto startup registry toggle."""
        original = is_auto_startup_enabled()
        try:
            # Test enable
            self.assertTrue(set_auto_startup(True))
            self.assertTrue(is_auto_startup_enabled())

            # Test disable
            self.assertTrue(set_auto_startup(False))
            self.assertFalse(is_auto_startup_enabled())
        finally:
            set_auto_startup(original)

    def test_launch_command_generation(self):
        cmd = get_default_launch_command()
        self.assertIn("app.py", cmd)
        self.assertIn("--minimized", cmd)

    def test_setup_wizard_instantiation(self):
        wizard = SetupWizard()
        self.assertIsNotNone(wizard)
        self.assertEqual(len(wizard.pageIds()), 6)
        # Verify StorageDirectoryPage is included
        from src.installer.setup_gui import StorageDirectoryPage
        storage_page = wizard.page(wizard.pageIds()[2])
        self.assertIsInstance(storage_page, StorageDirectoryPage)
        self.assertTrue(len(storage_page.edit_doc_folder.text()) > 0)

    def test_find_system_pythonw(self):
        from src.installer.setup_gui import find_system_pythonw
        py, pw = find_system_pythonw()
        self.assertTrue(os.path.exists(py), f"Python executable should exist: {py}")
        self.assertTrue(os.path.exists(pw), f"Pythonw executable should exist: {pw}")
        self.assertTrue(pw.lower().endswith("pythonw.exe") or pw.lower().endswith("python.exe"))


if __name__ == "__main__":
    unittest.main()
