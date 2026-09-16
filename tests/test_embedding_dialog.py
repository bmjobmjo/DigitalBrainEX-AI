"""
Unit tests for EmbeddingProgressDialog and EmbeddingWorker signal mechanics.
Verifies dual progress bars, label formatting, log updates, and completion states.
"""
import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.dialogs.embedding_progress_dialog import EmbeddingProgressDialog
from src.background.embedding_worker import EmbeddingWorker

# Ensure single QApplication instance
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestEmbeddingDialog(unittest.TestCase):

    def test_dialog_initialization(self):
        """Verify the dialog initializes with correct ranges, zero values, and initial button states."""
        dlg = EmbeddingProgressDialog(total_docs=150, title="Batch Embeddings")
        self.assertEqual(dlg.total_docs, 150)
        self.assertEqual(dlg.bar_overall.maximum(), 150)
        self.assertEqual(dlg.bar_overall.value(), 0)
        self.assertEqual(dlg.bar_current.maximum(), 100)
        self.assertEqual(dlg.bar_current.value(), 0)
        self.assertTrue(dlg.btn_cancel.isEnabled())
        self.assertFalse(dlg.btn_close.isEnabled())
        self.assertFalse(dlg.is_finished)
        dlg.close()

    def test_dialog_overall_progress_update(self):
        """Verify update_overall_progress updates progress bar and stats labels."""
        dlg = EmbeddingProgressDialog(total_docs=200)
        dlg.update_overall_progress(current=50, total=200, succeeded=48, failed=2)

        self.assertEqual(dlg.bar_overall.value(), 50)
        self.assertIn("50 / 200", dlg.lbl_overall_pct.text())
        self.assertIn("25.0%", dlg.lbl_overall_pct.text())
        self.assertIn("48", dlg.lbl_succeeded.text())
        self.assertIn("2", dlg.lbl_failed.text())
        self.assertIn("150", dlg.lbl_remaining.text())
        dlg.close()

    def test_dialog_item_progress_update(self):
        """Verify update_item_progress updates the intra-document progress bar, active item name, and stage text."""
        dlg = EmbeddingProgressDialog(total_docs=10)
        dlg.update_item_progress("Financial_Quarterly_2026.pdf", "Vectorizing chunk 5 of 12...", 42, 100)

        self.assertIn("Financial_Quarterly_2026.pdf", dlg.lbl_current_item.text())
        self.assertEqual(dlg.lbl_current_stage.text(), "Vectorizing chunk 5 of 12...")
        self.assertEqual(dlg.bar_current.value(), 42)
        dlg.close()

    def test_dialog_activity_log(self):
        """Verify append_log adds entries to the activity list widget."""
        dlg = EmbeddingProgressDialog(total_docs=5)
        dlg.append_log("✅ [1/5] Meeting_Notes.docx (4 chunks)")
        dlg.append_log("⚠️ [2/5] Empty_Doc.txt: No text found")

        self.assertEqual(dlg.list_activity.count(), 2)
        self.assertIn("Meeting_Notes.docx", dlg.list_activity.item(0).text())
        self.assertIn("Empty_Doc.txt", dlg.list_activity.item(1).text())
        dlg.close()

    def test_dialog_on_finished(self):
        """Verify on_finished switches button states, enables Close, and sets completion status."""
        dlg = EmbeddingProgressDialog(total_docs=50)
        dlg.on_finished(50, 48)

        self.assertTrue(dlg.is_finished)
        self.assertFalse(dlg.btn_cancel.isVisible())
        self.assertTrue(dlg.btn_close.isEnabled())
        self.assertIn("Indexing completed!", dlg.lbl_bottom_status.text())
        self.assertEqual(dlg.bar_overall.value(), 50)
        self.assertEqual(dlg.bar_current.value(), 100)
        dlg.close()

    def test_embedding_worker_signals_defined(self):
        """Verify EmbeddingWorker exposes the required dual-bar signals."""
        worker = EmbeddingWorker()
        self.assertTrue(hasattr(worker, "overall_progress"))
        self.assertTrue(hasattr(worker, "item_progress"))
        self.assertTrue(hasattr(worker, "activity_logged"))
        self.assertTrue(hasattr(worker, "progress_updated"))
        self.assertTrue(hasattr(worker, "all_completed"))


if __name__ == "__main__":
    unittest.main()
