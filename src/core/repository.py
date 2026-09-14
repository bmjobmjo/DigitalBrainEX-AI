"""
Unified Data Repository for DigitalBrainEX AI.
Provides clean, transactional CRUD methods for all business entities
backed by SQLAlchemy 2.0 and the existing SQLite database.
"""
from datetime import datetime, date
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import func, desc, or_, and_
from sqlalchemy.orm import Session
from src.core.database import get_db_session
from src.core.models import (
    Project,
    Document,
    DocumentCategory,
    Url,
    Task,
    Secret,
    TrackMe,
    Goal,
    WatchFolder,
    Embedding,
    DocumentChunk,
    ClipboardHistory,
)
from src.core.crypto import encrypt_des3, decrypt_des3
from src.core.logger import logger


def _build_multi_term_filter(search_str: Optional[str], columns: list):
    """
    Splits search_str by '+' (matching original C# DataManager.generateQueryPart).
    Each '+'-delimited term must be present in at least one of the given columns (AND across terms, OR across columns).
    """
    if not search_str or not search_str.strip():
        return None
    terms = [term.strip() for term in search_str.split("+") if term.strip()]
    if not terms:
        return None
    conditions = []
    for term in terms:
        term_pattern = f"%{term}%"
        conditions.append(or_(*[col.ilike(term_pattern) for col in columns]))
    return and_(*conditions)


class DataRepository:
    """Access layer for database entities with thread-safe session handling."""

    # -------------------------------------------------------------------------
    # PROJECTS
    # -------------------------------------------------------------------------
    @staticmethod
    def get_all_projects(status: Optional[str] = None, search: Optional[str] = None) -> List[Project]:
        with get_db_session() as session:
            query = session.query(Project)
            if status:
                query = query.filter(Project.Status == status)
            if search:
                filt = _build_multi_term_filter(search, [Project.ProjectName, Project.Desc, Project.Notes])
                if filt is not None:
                    query = query.filter(filt)
            return query.order_by(Project.ProjectName.asc()).all()

    @staticmethod
    def get_project_by_id(project_id: int) -> Optional[Project]:
        with get_db_session() as session:
            return session.query(Project).filter(Project.PojectID == project_id).first()

    @staticmethod
    def create_project(name: str, desc: str = "", notes: str = "", start_date: str = "") -> Project:
        now_int = int(datetime.now().timestamp())
        with get_db_session() as session:
            project = Project(
                ProjectName=name,
                Desc=desc,
                Notes=notes,
                StartDate=start_date or datetime.now().strftime("%Y-%m-%d"),
                StartDateInt=now_int,
                CreationDate=now_int,
                CreationDateInt=now_int,
                Status="Active",
                DirtyFlag=1,
            )
            session.add(project)
            session.flush()
            session.refresh(project)
            return project

    @staticmethod
    def update_project(project_id: int, **kwargs) -> bool:
        with get_db_session() as session:
            project = session.query(Project).filter(Project.PojectID == project_id).first()
            if not project:
                return False
            for k, v in kwargs.items():
                if hasattr(project, k):
                    setattr(project, k, v)
            project.DirtyFlag = 1
            return True

    @staticmethod
    def delete_project(project_id: int) -> bool:
        with get_db_session() as session:
            project = session.query(Project).filter(Project.PojectID == project_id).first()
            if project:
                session.delete(project)
                return True
            return False

    # -------------------------------------------------------------------------
    # TASKS & REMINDERS
    # -------------------------------------------------------------------------
    @staticmethod
    def get_tasks(
        project_id: Optional[str] = None,
        status: Optional[str] = "Active",
        search: Optional[str] = None,
    ) -> List[Task]:
        with get_db_session() as session:
            query = session.query(Task)
            if project_id and str(project_id) != "0":
                query = query.filter(Task.ProjectID == str(project_id))
            if status and status != "All":
                query = query.filter(Task.Status == status)
            if search:
                filt = _build_multi_term_filter(search, [Task.TaskName, Task.TaskDesc, Task.ProjectName])
                if filt is not None:
                    query = query.filter(filt)
            return query.order_by(Task.DueOn.asc(), Task.Priority.desc()).all()

    @staticmethod
    def get_todays_tasks(project_id: Optional[str] = None) -> List[Task]:
        today_str = date.today().strftime("%Y-%m-%d")
        with get_db_session() as session:
            query = session.query(Task).filter(
                Task.Status == "Active",
                or_(Task.DueOn.like(f"{today_str}%"), Task.ToDaysTask == today_str),
            )
            if project_id and str(project_id) != "0":
                query = query.filter(Task.ProjectID == str(project_id))
            return query.order_by(Task.Priority.desc(), Task.TaskID.asc()).all()

    @staticmethod
    def create_task(
        name: str,
        desc: str = "",
        due_on: str = "",
        project_id: str = "0",
        project_name: str = "General",
        rem_type: str = "No",
        reminder_time: str = "00:00",
        priority: int = 0,
        task_type: str = "T",
    ) -> Task:
        with get_db_session() as session:
            task = Task(
                TaskName=name,
                TaskDesc=desc,
                Type=task_type,
                DueOn=due_on or datetime.now().strftime("%Y-%m-%d"),
                ProjectID=str(project_id),
                ProjectName=project_name,
                Status="Active",
                RemType=rem_type,
                ReminderTimeHHMM=reminder_time,
                Priority=priority,
                DirtyFlag=1,
            )
            session.add(task)
            session.flush()
            session.refresh(task)
            return task

    @staticmethod
    def update_task(task_id: int, **kwargs) -> bool:
        with get_db_session() as session:
            task = session.query(Task).filter(Task.TaskID == task_id).first()
            if not task:
                return False
            for k, v in kwargs.items():
                if hasattr(task, k):
                    setattr(task, k, v)
            task.DirtyFlag = 1
            return True

    @staticmethod
    def delete_task(task_id: int) -> bool:
        with get_db_session() as session:
            task = session.query(Task).filter(Task.TaskID == task_id).first()
            if task:
                session.delete(task)
                return True
            return False

    # -------------------------------------------------------------------------
    # DOCUMENTS, CODE SNIPPETS, MINUTES, NOTES
    # -------------------------------------------------------------------------
    @staticmethod
    def get_documents(
        project_id: Optional[int] = None,
        doc_type: Optional[int] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        exclude_categories: Optional[List[str]] = None,
    ) -> List[Document]:
        with get_db_session() as session:
            query = session.query(Document)
            if project_id and project_id != 0:
                query = query.filter(Document.PojectID == project_id)
            if doc_type is not None:
                query = query.filter(Document.Type == doc_type)
            if category and category != "All" and category != "All Categories":
                query = query.filter(Document.Category == category)
            elif exclude_categories:
                query = query.filter(~Document.Category.in_(exclude_categories))
            if search:
                filt = _build_multi_term_filter(
                    search,
                    [Document.DocumentName, Document.DocumentURI, Document.Desc, Document.Notes, Document.ProjectName, Document.Category],
                )
                if filt is not None:
                    query = query.filter(filt)
            return query.order_by(Document.DocumentID.desc()).all()

    @staticmethod
    def get_notes(
        project_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Document]:
        """Queries documents for personal diary notes (Category == 'PlainNotes')."""
        with get_db_session() as session:
            query = session.query(Document).filter(Document.Category == "PlainNotes")
            if project_id and project_id != 0:
                query = query.filter(Document.PojectID == project_id)
            if search:
                filt = _build_multi_term_filter(
                    search,
                    [Document.DocumentName, Document.Desc, Document.Notes, Document.ProjectName],
                )
                if filt is not None:
                    query = query.filter(filt)
            return query.order_by(Document.DocumentID.desc()).all()

    @staticmethod
    def get_minutes(
        project_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Document]:
        """Queries documents for meeting minutes (Category == 'Minutes')."""
        with get_db_session() as session:
            query = session.query(Document).filter(
                Document.Category == "Minutes",
                Document.Type.in_([0, 8, 9, 10, 11]),
            )
            if project_id and project_id != 0:
                query = query.filter(Document.PojectID == project_id)
            if search:
                filt = _build_multi_term_filter(
                    search,
                    [Document.DocumentName, Document.Desc, Document.Notes, Document.ProjectName],
                )
                if filt is not None:
                    query = query.filter(filt)
            return query.order_by(Document.DocumentID.desc()).all()

    @staticmethod
    def get_code_snippets(
        project_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Document]:
        """Queries documents for code snippets and code files (Type IN (4, 5))."""
        with get_db_session() as session:
            query = session.query(Document).filter(Document.Type.in_([4, 5]))
            if project_id and project_id != 0:
                query = query.filter(Document.PojectID == project_id)
            if search:
                filt = _build_multi_term_filter(
                    search,
                    [Document.DocumentName, Document.Desc, Document.Notes, Document.Language, Document.ProjectName],
                )
                if filt is not None:
                    query = query.filter(filt)
            return query.order_by(Document.DocumentID.desc()).all()

    @staticmethod
    def get_document_by_id(doc_id: int) -> Optional[Document]:
        with get_db_session() as session:
            return session.query(Document).filter(Document.DocumentID == doc_id).first()

    @staticmethod
    def create_document(
        name: str,
        uri: str = "",
        desc: str = "",
        notes: str = "",
        project_id: int = 0,
        project_name: str = "General",
        category: str = "General",
        doc_type: int = 0,
        language: str = "Plain",
        embedding_status: str = "PENDING",
    ) -> Document:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        now_int = int(datetime.now().timestamp())
        with get_db_session() as session:
            doc = Document(
                PojectID=project_id,
                ProjectName=project_name,
                DocumentName=name,
                DocumentURI=uri,
                Desc=desc,
                Notes=notes,
                Category=category,
                Type=doc_type,
                Language=language,
                AddedOn=now_str,
                AddedOnInt=now_int,
                ModifiedDate=now_int,
                DirtyFlag=1,
                EmbeddingStatus=embedding_status,
                EmbeddingError=None,
            )
            session.add(doc)
            session.flush()
            session.refresh(doc)
            return doc

    @staticmethod
    def update_document(doc_id: int, **kwargs) -> bool:
        with get_db_session() as session:
            doc = session.query(Document).filter(Document.DocumentID == doc_id).first()
            if not doc:
                return False
            for k, v in kwargs.items():
                if hasattr(doc, k):
                    setattr(doc, k, v)
            doc.ModifiedDate = int(datetime.now().timestamp())
            doc.DirtyFlag = 1
            return True

    @staticmethod
    def delete_document(doc_id: int) -> bool:
        with get_db_session() as session:
            doc = session.query(Document).filter(Document.DocumentID == doc_id).first()
            if doc:
                # Also clean up any fine-grained document chunks
                session.query(DocumentChunk).filter(DocumentChunk.file_id == doc_id).delete()
                session.delete(doc)
                return True
            return False

    @staticmethod
    def get_document_categories() -> List[DocumentCategory]:
        with get_db_session() as session:
            return session.query(DocumentCategory).order_by(DocumentCategory.CatogoryName.asc()).all()

    # -------------------------------------------------------------------------
    # DOCUMENT EMBEDDING & CHUNKS (RAG)
    # -------------------------------------------------------------------------
    @staticmethod
    def update_document_embedding_status(doc_id: int, status: str, error: Optional[str] = None) -> bool:
        """Updates the embedding status and optional error message for a document."""
        with get_db_session() as session:
            doc = session.query(Document).filter(Document.DocumentID == doc_id).first()
            if not doc:
                return False
            doc.EmbeddingStatus = status
            doc.EmbeddingError = error
            doc.ModifiedDate = int(datetime.now().timestamp())
            return True

    @staticmethod
    def get_documents_by_embedding_status(status: str) -> List[Document]:
        """Retrieves documents matching the given embedding status (e.g. 'PENDING', 'FAILED')."""
        with get_db_session() as session:
            return session.query(Document).filter(Document.EmbeddingStatus == status).order_by(Document.DocumentID.asc()).all()

    @staticmethod
    def save_document_chunks(file_id: int, chunks: List[Dict[str, Any]]) -> int:
        """
        Replaces any existing chunks for file_id with new chunks.
        chunks: List of dicts containing: chunk_index, chunk_text, embedding, page_or_section, model_name, model_version.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_db_session() as session:
            session.query(DocumentChunk).filter(DocumentChunk.file_id == file_id).delete()
            for ch in chunks:
                chunk_obj = DocumentChunk(
                    file_id=file_id,
                    chunk_index=ch.get("chunk_index", 0),
                    chunk_text=ch.get("chunk_text", ""),
                    embedding=ch.get("embedding", b""),
                    page_or_section=ch.get("page_or_section"),
                    model_name=ch.get("model_name"),
                    model_version=ch.get("model_version"),
                    created_at=ch.get("created_at") or now_str,
                )
                session.add(chunk_obj)
            return len(chunks)

    @staticmethod
    def get_chunks_for_file(file_id: int) -> List[DocumentChunk]:
        """Returns all chunks for a specific document ordered by chunk_index."""
        with get_db_session() as session:
            return session.query(DocumentChunk).filter(DocumentChunk.file_id == file_id).order_by(DocumentChunk.chunk_index.asc()).all()

    @staticmethod
    def get_all_chunks() -> List[DocumentChunk]:
        """Returns all document chunks across all indexed documents."""
        with get_db_session() as session:
            return session.query(DocumentChunk).all()

    # -------------------------------------------------------------------------
    # URLS
    # -------------------------------------------------------------------------
    @staticmethod
    def get_urls(
        project_id: Optional[int] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Url]:
        with get_db_session() as session:
            query = session.query(Url)
            if project_id and project_id != 0:
                query = query.filter(Url.PojectID == project_id)
            if category and category != "All":
                query = query.filter(Url.Category == category)
            if search:
                filt = _build_multi_term_filter(
                    search,
                    [Url.UrlName, Url.Url, Url.Notes, Url.ProjectName, Url.Category],
                )
                if filt is not None:
                    query = query.filter(filt)
            return query.order_by(Url.UrlID.desc()).all()

    @staticmethod
    def create_url(
        url: str,
        name: str,
        notes: str = "",
        category: str = "General",
        project_id: int = 0,
        project_name: str = "General",
    ) -> Url:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        now_int = int(datetime.now().timestamp())
        with get_db_session() as session:
            url_obj = Url(
                Url=url,
                UrlName=name,
                Notes=notes,
                Category=category,
                PojectID=project_id,
                ProjectName=project_name,
                AddedOn=now_str,
                AddedOnInt=now_int,
                DirtyFlag=1,
            )
            session.add(url_obj)
            session.flush()
            session.refresh(url_obj)
            return url_obj

    @staticmethod
    def delete_url(url_id: int) -> bool:
        with get_db_session() as session:
            url_obj = session.query(Url).filter(Url.UrlID == url_id).first()
            if url_obj:
                session.delete(url_obj)
                return True
            return False

    # -------------------------------------------------------------------------
    # SECRETS VAULT
    # -------------------------------------------------------------------------
    @staticmethod
    def get_secrets(project_id: Optional[str] = None, search: Optional[str] = None) -> List[Secret]:
        with get_db_session() as session:
            query = session.query(Secret).filter(Secret.Status == "Active")
            if project_id and str(project_id) != "0":
                query = query.filter(Secret.ProjectID == str(project_id))
            if search:
                filt = _build_multi_term_filter(
                    search,
                    [Secret.SecretName, Secret.ApplicationURL, Secret.Desc, Secret.ProjectName],
                )
                if filt is not None:
                    query = query.filter(filt)
            return query.order_by(Secret.SecretName.asc()).all()

    @staticmethod
    def get_secret_by_id(secret_id: int) -> Optional[Secret]:
        with get_db_session() as session:
            return session.query(Secret).filter(Secret.SecretID == secret_id).first()

    @staticmethod
    def create_secret(
        secret_name: str,
        app_url: str,
        identity: str,
        password: str,
        desc: str = "",
        project_id: str = "0",
        project_name: str = "General",
        secret_key: Optional[str] = None,
    ) -> Secret:
        """
        Creates a new Secret. If secret_key is provided, Identity and Password are
        encrypted using TripleDES before writing to database.
        """
        enc_identity = encrypt_des3(secret_key, identity) if secret_key else identity
        enc_password = encrypt_des3(secret_key, password) if secret_key else password

        with get_db_session() as session:
            secret = Secret(
                SecretName=secret_name,
                ApplicationURL=app_url,
                Identity=enc_identity,
                Password=enc_password,
                Desc=desc,
                ProjectID=str(project_id),
                ProjectName=project_name,
                Status="Active",
                UpdatedON=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                DirtyFlag=1,
            )
            session.add(secret)
            session.flush()
            session.refresh(secret)
            return secret

    @staticmethod
    def update_secret(secret_id: int, **kwargs) -> bool:
        with get_db_session() as session:
            secret = session.query(Secret).filter(Secret.SecretID == secret_id).first()
            if not secret:
                return False
            for k, v in kwargs.items():
                if hasattr(secret, k):
                    setattr(secret, k, v)
            secret.UpdatedON = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            secret.DirtyFlag = 1
            return True

    @staticmethod
    def delete_secret(secret_id: int) -> bool:
        with get_db_session() as session:
            secret = session.query(Secret).filter(Secret.SecretID == secret_id).first()
            if secret:
                session.delete(secret)
                return True
            return False

    @staticmethod
    def encrypt_secret_value(key: str, plain_text: str) -> str:
        """Encrypts a secret string using TripleDES matching C# CryptHelper."""
        return encrypt_des3(key, plain_text)

    @staticmethod
    def decrypt_secret_value(key: str, cipher_b64: str) -> str:
        """Decrypts a secret string using TripleDES matching C# CryptHelper."""
        return decrypt_des3(key, cipher_b64)

    @staticmethod
    def decrypt_secret_credentials(secret: Secret, key: str) -> Tuple[str, str]:
        """Decrypts and returns (identity, password) using the provided master key."""
        try:
            dec_iden = decrypt_des3(key, secret.Identity or "")
            dec_pass = decrypt_des3(key, secret.Password or "")
            return dec_iden, dec_pass
        except Exception as e:
            logger.error(f"Failed to decrypt secret id={secret.SecretID}: {e}")
            raise

    # -------------------------------------------------------------------------
    # TRACKME (ACTIVE WINDOW LOGGING)
    # -------------------------------------------------------------------------
    @staticmethod
    def log_activity(
        app_name: str,
        window_title: str,
        seconds: int = 5,
        project_id: int = 0,
        project_name: str = "General",
    ) -> TrackMe:
        with get_db_session() as session:
            entry = TrackMe(
                ProjectID=project_id,
                ProjectName=project_name,
                Application=app_name,
                WindowTitle=window_title,
                Seconds=seconds,
                DateTime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            session.add(entry)
            session.flush()
            session.refresh(entry)
            return entry

    @staticmethod
    def get_recent_activity(limit: int = 100) -> List[TrackMe]:
        with get_db_session() as session:
            return session.query(TrackMe).order_by(TrackMe.TrackID.desc()).limit(limit).all()

    @staticmethod
    def get_application_usage_summary(date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        target_date = date_str or date.today().strftime("%Y-%m-%d")
        with get_db_session() as session:
            rows = (
                session.query(
                    TrackMe.Application,
                    func.sum(TrackMe.Seconds).label("total_seconds"),
                    func.count(TrackMe.TrackID).label("sample_count"),
                )
                .filter(TrackMe.DateTime.like(f"{target_date}%"))
                .group_by(TrackMe.Application)
                .order_by(desc("total_seconds"))
                .all()
            )
            return [
                {
                    "application": r[0],
                    "total_seconds": r[1] or 0,
                    "sample_count": r[2] or 0,
                }
                for r in rows
            ]

    # -------------------------------------------------------------------------
    # CLIPBOARD HISTORY
    # -------------------------------------------------------------------------
    @staticmethod
    def add_clipboard_entry(
        content_type: str,
        text_content: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> Optional[ClipboardHistory]:
        if not text_content and not image_path:
            return None
        with get_db_session() as session:
            # Avoid duplicate consecutive entries if text matches latest
            if content_type == "Text" and text_content:
                latest = (
                    session.query(ClipboardHistory)
                    .filter(ClipboardHistory.ContentType == "Text")
                    .order_by(ClipboardHistory.ID.desc())
                    .first()
                )
                if latest and latest.TextContent == text_content:
                    return latest

            entry = ClipboardHistory(
                ContentType=content_type,
                TextContent=text_content,
                ImagePath=image_path,
                AddedOn=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            session.add(entry)
            session.flush()
            session.refresh(entry)
            return entry

    @staticmethod
    def get_clipboard_history(
        limit: int = 100,
        search: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> List[ClipboardHistory]:
        with get_db_session() as session:
            query = session.query(ClipboardHistory)
            if content_type and content_type != "All":
                query = query.filter(ClipboardHistory.ContentType == content_type)
            if search:
                filt = _build_multi_term_filter(
                    search,
                    [ClipboardHistory.TextContent, ClipboardHistory.ImagePath],
                )
                if filt is not None:
                    query = query.filter(filt)
            return query.order_by(ClipboardHistory.ID.desc()).limit(limit).all()

    @staticmethod
    def delete_clipboard_entry(entry_id: int) -> bool:
        with get_db_session() as session:
            entry = session.query(ClipboardHistory).filter(ClipboardHistory.ID == entry_id).first()
            if entry:
                session.delete(entry)
                return True
            return False

    @staticmethod
    def clear_clipboard_history() -> bool:
        with get_db_session() as session:
            session.query(ClipboardHistory).delete()
            return True

    # -------------------------------------------------------------------------
    # WATCH FOLDER
    # -------------------------------------------------------------------------
    @staticmethod
    def get_watch_folders() -> List[str]:
        with get_db_session() as session:
            rows = session.query(WatchFolder).all()
            return [r.FolderPath for r in rows if r.FolderPath]

    @staticmethod
    def add_watch_folder(folder_path: str) -> bool:
        with get_db_session() as session:
            existing = session.query(WatchFolder).filter(WatchFolder.FolderPath == folder_path).first()
            if not existing:
                session.add(WatchFolder(FolderPath=folder_path))
                return True
            return False

    @staticmethod
    def remove_watch_folder(folder_path: str) -> bool:
        with get_db_session() as session:
            item = session.query(WatchFolder).filter(WatchFolder.FolderPath == folder_path).first()
            if item:
                session.delete(item)
                return True
            return False
