"""
Background QThread worker for uploading local documents to Google Drive.
"""
from PyQt6.QtCore import QThread, pyqtSignal
from src.services.gdrive_service import gdrive_service


class GDriveUploadWorker(QThread):
    """Background worker for backing up pending documents to Google Drive."""

    progress_updated = pyqtSignal(int, int, str, str)  # current, total, doc_name, status
    all_completed = pyqtSignal(int, int, list)         # total, succeeded, errors
    auth_required = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        self._is_cancelled = False

        if not gdrive_service.is_authenticated():
            # Try non-interactive auth
            if not gdrive_service.authenticate(interactive=False):
                self.auth_required.emit()
                self.all_completed.emit(0, 0, ["Authentication required. Please authenticate Google Drive in Settings."])
                return

        def on_progress(curr, tot, name, msg):
            self.progress_updated.emit(curr, tot, name, msg)

        def check_cancelled():
            return self._is_cancelled

        total, succeeded, errors = gdrive_service.upload_pending_documents(
            progress_callback=on_progress,
            cancel_check=check_cancelled,
        )
        self.all_completed.emit(total, succeeded, errors)
