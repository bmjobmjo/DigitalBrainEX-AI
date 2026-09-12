"""
Smoke test for PyQt6 UI components and views.
Verifies that all views and MainWindow instantiate without errors.
"""
import unittest
import os
import sys

# Ensure root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.ui.theme import apply_theme

# Create headless QApplication for testing
app = QApplication.instance() or QApplication(["test_ui"])


class TestUISmoke(unittest.TestCase):

    def test_main_window_instantiation(self):
        apply_theme(app)
        window = MainWindow()
        self.assertIsNotNone(window)
        self.assertEqual(window.view_stack.count(), 12)
        print("MainWindow and all 12 views instantiated successfully!")

        # Verify each view inside stack
        for i in range(12):
            w = window.view_stack.widget(i)
            self.assertIsNotNone(w)
            print(f"  - View {i}: {w.__class__.__name__} OK")

    def test_switch_to_notes_fast(self):
        import time
        apply_theme(app)
        window = MainWindow()
        window.show()
        app.processEvents()

        t0 = time.perf_counter()
        window.sidebar.select_module_by_name("Notes")
        app.processEvents()
        elapsed = time.perf_counter() - t0

        self.assertLess(elapsed, 0.5, f"Switching to Notes took too long: {elapsed:.3f}s")
        notes_view = window.view_notes
        self.assertGreater(notes_view.table.rowCount(), 900)

        # Verify selecting a row
        notes_view.table.selectRow(0)
        app.processEvents()
        selected_id = notes_view._get_selected_note_id()
        self.assertIsNotNone(selected_id)
        self.assertGreater(selected_id, 0)
        print(f"Notes view switched and loaded {notes_view.table.rowCount()} rows in {elapsed:.4f}s!")
        window.close()

    def test_switch_all_views_smooth(self):
        apply_theme(app)
        window = MainWindow()
        window.show()
        app.processEvents()

        modules = [
            "Projects", "Tasks", "Documents", "URLs",
            "Code Snippets", "Minutes", "FileManager", "Notes",
            "Secrets", "TrackMe", "AskMe", "Settings"
        ]
        for mod in modules:
            window.sidebar.select_module_by_name(mod)
            app.processEvents()

        print("Smooth navigation verified across all 12 modules!")
        window.close()


if __name__ == "__main__":
    unittest.main()
