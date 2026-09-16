"""
Google Drive Document Backup Service for DigitalBrainEX AI.
Ports C# GDocumentsSync.cs functionality to upload and backup local documents
to the 'DigitalBrainEX/Documents' directory in Google Drive.
"""
import os
import mimetypes
from typing import Optional, List, Tuple, Callable
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.core.repository import DataRepository
from src.config import resolve_document_path, get_doc_folder
from src.core.logger import logger

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]

FOLDER_NAME = "DigitalBrainEX"
SUBFOLDER_NAME = "Documents"


class GDriveService:
    """Service to handle authentication and document backup to Google Drive."""

    def __init__(self):
        self._service = None
        self._creds = None

    @staticmethod
    def get_credentials_file() -> Optional[str]:
        """Locates the gdrivecred.json client secrets configuration file."""
        candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "gdrivecred.json"),
            os.path.join(get_doc_folder(), "gdrivecred.json"),
            os.path.join(os.path.expanduser("~"), "AppData", "Local", "DigitalBrainEX", "gdrivecred.json"),
            r"d:\Works\DigitalBrainEX\ScreenShot\DevDiaryControls\gdrivecred.json",
            r"d:\Works\DigitalBrainEX\ScreenShot\DigitalBrainExSetup\CommonFiles\gdrivecred.json",
        ]
        for c in candidates:
            if c and os.path.exists(c):
                return c
        return None

    @staticmethod
    def get_token_file() -> str:
        """Returns path where OAuth2 token is stored."""
        token_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "DigitalBrainEX")
        os.makedirs(token_dir, exist_ok=True)
        return os.path.join(token_dir, "gdrive_token.json")

    def is_configured(self) -> bool:
        """Returns True if client credentials JSON exists."""
        return self.get_credentials_file() is not None

    def is_authenticated(self) -> bool:
        """Returns True if a valid or refreshable token is saved."""
        token_file = self.get_token_file()
        if not os.path.exists(token_file):
            return False
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            return creds and (creds.valid or creds.refresh_token is not None)
        except Exception:
            return False

    def authenticate(self, interactive: bool = True) -> bool:
        """Authenticates with Google Drive and caches credentials."""
        token_file = self.get_token_file()
        creds = None

        if os.path.exists(token_file):
            try:
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            except Exception as e:
                logger.warning(f"Could not load stored Google Drive token: {e}")

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(token_file, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())
                self._creds = creds
                self._service = build("drive", "v3", credentials=self._creds)
                return True
            except Exception as re:
                logger.warning(f"Token refresh failed: {re}")
                creds = None

        if not creds or not creds.valid:
            if not interactive:
                return False

            cred_file = self.get_credentials_file()
            if not cred_file:
                logger.error("gdrivecred.json not found.")
                return False

            flow = InstalledAppFlow.from_client_secrets_file(cred_file, SCOPES)
            creds = flow.run_local_server(port=0)

            with open(token_file, "w", encoding="utf-8") as f:
                f.write(creds.to_json())

        self._creds = creds
        self._service = build("drive", "v3", credentials=self._creds)
        logger.info("Google Drive API authenticated successfully.")
        return True

    def get_service(self):
        """Returns active Drive API service, authenticating if necessary."""
        if self._service is None:
            if not self.authenticate(interactive=False):
                raise RuntimeError("Google Drive is not authenticated. Please authenticate first.")
        return self._service

    def get_or_create_documents_folder(self) -> str:
        """Finds or creates DigitalBrainEX/Documents folder hierarchy on Drive."""
        service = self.get_service()

        # 1. Check parent folder
        query = f"mimeType='application/vnd.google-apps.folder' and trashed=false and name='{FOLDER_NAME}'"
        results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        files = results.get("files", [])

        if files:
            parent_id = files[0]["id"]
        else:
            meta = {
                "name": FOLDER_NAME,
                "mimeType": "application/vnd.google-apps.folder",
            }
            folder = service.files().create(body=meta, fields="id").execute()
            parent_id = folder.get("id")
            logger.info(f"Created Google Drive folder '{FOLDER_NAME}' (ID: {parent_id})")

        # 2. Check Documents subfolder
        sub_query = f"mimeType='application/vnd.google-apps.folder' and trashed=false and name='{SUBFOLDER_NAME}' and '{parent_id}' in parents"
        sub_results = service.files().list(q=sub_query, spaces="drive", fields="files(id, name)").execute()
        sub_files = sub_results.get("files", [])

        if sub_files:
            return sub_files[0]["id"]
        else:
            meta = {
                "name": SUBFOLDER_NAME,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            }
            sub_folder = service.files().create(body=meta, fields="id").execute()
            docs_folder_id = sub_folder.get("id")
            logger.info(f"Created Google Drive subfolder '{SUBFOLDER_NAME}' (ID: {docs_folder_id})")
            return docs_folder_id

    def upload_file(self, local_path: str, remote_filename: Optional[str] = None) -> Optional[str]:
        """Uploads a local file to DigitalBrainEX/Documents in Google Drive."""
        if not local_path or not os.path.exists(local_path):
            return None

        service = self.get_service()
        folder_id = self.get_or_create_documents_folder()

        name = remote_filename or os.path.basename(local_path)
        mime_type, _ = mimetypes.guess_type(local_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        # Check if already exists in Documents folder
        check_q = f"trashed=false and name='{name}' and '{folder_id}' in parents"
        existing = service.files().list(q=check_q, fields="files(id)").execute().get("files", [])
        if existing:
            return existing[0]["id"]

        media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
        file_metadata = {
            "name": name,
            "parents": [folder_id],
        }

        created = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        file_id = created.get("id")
        logger.info(f"Uploaded file '{name}' to Google Drive (ID: {file_id})")
        return file_id

    def upload_pending_documents(
        self,
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Tuple[int, int, List[str]]:
        """
        Uploads all local documents that have not yet been backed up to Google Drive (DocGUID is empty).
        Updates DocGUID in SQLite upon success.
        """
        if not self.authenticate(interactive=False):
            return 0, 0, ["Google Drive authentication required."]

        docs = DataRepository.get_documents_needing_gdrive_upload()
        # Filter for local files that actually exist
        upload_candidates = []
        for d in docs:
            uri = d.DocumentURI or ""
            if (
                uri.lower().startswith("http://")
                or uri.lower().startswith("https://")
                or uri.lower().startswith("drive.google.com")
            ):
                continue
            res_path = resolve_document_path(uri)
            if res_path and os.path.exists(res_path) and os.path.isfile(res_path):
                upload_candidates.append((d, res_path))

        total = len(upload_candidates)
        succeeded = 0
        errors = []

        if total == 0:
            return 0, 0, []

        for idx, (doc, file_path) in enumerate(upload_candidates, 1):
            if cancel_check and cancel_check():
                logger.info("Google Drive upload cancelled by user.")
                break

            doc_name = doc.DocumentName or os.path.basename(file_path)
            if progress_callback:
                progress_callback(idx, total, doc_name, "Uploading to Google Drive...")

            try:
                file_id = self.upload_file(file_path, os.path.basename(file_path))
                if file_id:
                    DataRepository.update_document(doc.DocumentID, DocGUID=file_id)
                    succeeded += 1
                    if progress_callback:
                        progress_callback(idx, total, doc_name, "Uploaded successfully")
            except Exception as e:
                err_str = f"{doc_name}: {e}"
                logger.error(f"Error uploading {doc_name} to Google Drive: {e}")
                errors.append(err_str)
                if progress_callback:
                    progress_callback(idx, total, doc_name, f"Failed: {str(e)[:35]}")

        return total, succeeded, errors


# Singleton instance
gdrive_service = GDriveService()
