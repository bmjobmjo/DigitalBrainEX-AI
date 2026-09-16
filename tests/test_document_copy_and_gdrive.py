"""
Unit tests for document file copying to project folders and Google Drive service integration.
"""
import sys
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from src.core.repository import DataRepository
from src.config import get_doc_folder
from src.services.gdrive_service import gdrive_service, GDriveService

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestDocumentCopyAndGDrive(unittest.TestCase):

    def test_gdrive_credentials_found(self):
        """Verify gdrivecred.json is located and service reports configured."""
        cred_file = gdrive_service.get_credentials_file()
        self.assertIsNotNone(cred_file)
        self.assertTrue(os.path.exists(cred_file))
        self.assertTrue(gdrive_service.is_configured())

    def test_documents_needing_gdrive_upload_query(self):
        """Verify DataRepository query for un-backed-up documents."""
        unbacked = DataRepository.get_documents_needing_gdrive_upload()
        self.assertIsInstance(unbacked, list)
        for doc in unbacked[:10]:
            self.assertTrue(doc.DocGUID is None or doc.DocGUID == "")
            self.assertTrue(doc.DocumentURI is not None and doc.DocumentURI != "")

    def test_document_copy_on_save(self):
        """Verify adding a document copies the local file to DocFolder/{proj_id}/{filename} and stores relative URI."""
        from src.ui.dialogs.document_editor_dlg import DocumentEditorDialog

        with tempfile.NamedTemporaryFile("w", suffix=".pdf", delete=False) as f:
            f.write("Sample document content")
            src_temp_file = f.name

        doc_id = None
        try:
            dlg = DocumentEditorDialog(default_project_id=42)
            dlg.edit_name.setText("Test Copy Document")
            dlg.edit_uri.setText(src_temp_file)

            # Mock combo box to return project_id=42
            dlg.combo_proj.clear()
            dlg.combo_proj.addItem("Project 42", 42)
            dlg.combo_proj.setCurrentIndex(0)

            dlg._save_document()
            doc_id = dlg.saved_doc_id
            self.assertIsNotNone(doc_id)

            saved_doc = DataRepository.get_document_by_id(doc_id)
            self.assertIsNotNone(saved_doc)

            # Expected relative URI format: \42\<filename>
            filename = os.path.basename(src_temp_file)
            self.assertEqual(saved_doc.DocumentURI, f"\\42\\{filename}")

            # Verify file was physically copied to DocFolder/42/<filename>
            expected_dest = os.path.join(get_doc_folder(), "42", filename)
            self.assertTrue(os.path.exists(expected_dest))

            # Cleanup copied file
            if os.path.exists(expected_dest):
                os.remove(expected_dest)

        finally:
            if doc_id:
                DataRepository.delete_document(doc_id)
            if os.path.exists(src_temp_file):
                os.remove(src_temp_file)

    @patch("src.services.gdrive_service.GDriveService.upload_file")
    @patch("src.services.gdrive_service.GDriveService.authenticate")
    def test_upload_pending_documents_mocked(self, mock_auth, mock_upload):
        """Verify upload_pending_documents updates DocGUID upon successful Google Drive upload."""
        mock_auth.return_value = True
        mock_upload.return_value = "gdrive-file-id-12345"

        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("Test upload content")
            local_file = f.name

        doc = DataRepository.create_document(
            name="Test Upload Doc",
            uri=local_file,
            project_id=0,
        )
        doc_id = doc.DocumentID

        try:
            total, succ, errs = gdrive_service.upload_pending_documents()
            self.assertGreaterEqual(total, 1)

            reloaded = DataRepository.get_document_by_id(doc_id)
            self.assertEqual(reloaded.DocGUID, "gdrive-file-id-12345")
        finally:
            DataRepository.delete_document(doc_id)
            if os.path.exists(local_file):
                os.remove(local_file)


if __name__ == "__main__":
    unittest.main()
