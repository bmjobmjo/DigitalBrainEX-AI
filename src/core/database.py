"""
Database Connection and Session Management for DigitalBrainEX AI.
Connects directly to the existing SQLite database via SQLAlchemy 2.0.
"""
from contextlib import contextmanager
from typing import Generator, Optional
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from src.config import DB_PATH, DATABASE_URI
from src.core.logger import logger

Base = declarative_base()

_engine = None
_SessionFactory = None


def get_engine(db_uri: str = None):
    """Creates or returns the cached SQLAlchemy engine with SQLite pragmas."""
    global _engine, _SessionFactory
    if _engine is None:
        target_uri = db_uri or DATABASE_URI
        logger.info(f"Initializing database engine with URI: {target_uri}")

        _engine = create_engine(
            target_uri,
            connect_args={"check_same_thread": False, "timeout": 30.0},
            echo=False,
            future=True,
        )

        # Optimize SQLite performance with WAL and PRAGMA tweaks
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA busy_timeout=5000")
            finally:
                cursor.close()

        _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def get_session_factory():
    """Returns the configured sessionmaker."""
    global _SessionFactory
    if _SessionFactory is None:
        get_engine()
    return _SessionFactory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic commit/rollback.
    Usage:
        with get_db_session() as session:
            session.add(item)
    """
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction error: {e}", exc_info=True)
        raise
    finally:
        session.close()


def seed_default_data_if_empty():
    """Seeds default project and standard categories if the database is brand new and empty."""
    try:
        from src.core.models import Project, DocumentCategory
        with get_db_session() as session:
            proj_count = session.query(Project).count()
            if proj_count == 0:
                default_proj = Project(
                    PojectID=1,
                    ProjectName="General",
                    Desc="To manage common and general things",
                    Notes="Anything that is not fall in to any special catogory",
                    Status="Active",
                    CreationDate="12/20/2021",
                    ProjGUID="0975f4f2-89d7-4ca5-9e4d-1a767318b1cc",
                )
                session.add(default_proj)
                logger.info("Seeded default 'General' project.")

            cat_count = session.query(DocumentCategory).count()
            if cat_count == 0:
                default_cats = [
                    (1, "General"), (2, "Requirements"), (3, "Design"), (4, "TechDoc"),
                    (5, "Minutes"), (6, "Plan"), (7, "Schedule"), (8, "Estimate"),
                    (9, "P&L"), (10, "TestCases"), (11, "IssueList"), (12, "Accounts"),
                    (13, "HR"), (14, "Resumes")
                ]
                for cid, name in default_cats:
                    session.add(DocumentCategory(CatgoryID=cid, CatogoryName=name))
                logger.info("Seeded 14 standard document categories.")
    except Exception as e:
        logger.warning(f"Could not check/seed default data: {e}")


def init_db():
    """Initializes tables if not already present, runs schema migrations, and seeds default data."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    # Safe SQLite schema migration for documents table
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("PRAGMA table_info(documents)"))
            existing_cols = {row[1] for row in result.fetchall()}
            
            if "EmbeddingStatus" not in existing_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN EmbeddingStatus TEXT DEFAULT 'PENDING'"))
                logger.info("Migrated schema: added EmbeddingStatus column to documents table.")
            
            if "EmbeddingError" not in existing_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN EmbeddingError TEXT"))
                logger.info("Migrated schema: added EmbeddingError column to documents table.")

            # Ensure index on document_chunks(file_id)
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON document_chunks(file_id)"))
            conn.commit()
    except Exception as e:
        logger.warning(f"Schema migration warning: {e}")

    logger.info("Database schema initialized/verified.")
    seed_default_data_if_empty()


def take_startup_db_backup() -> Optional[str]:
    """
    Creates a backup copy of the active database on startup.
    Matches C# DevDiaryManager.TakeDBBackup():
    Backup path: {DocFolder}/DevDiary-{DD-MM-YYYY}.db3
    Uses sqlite3 online backup to guarantee safe, non-corrupted copy.
    """
    import sqlite3
    from datetime import datetime
    import shutil
    from typing import Optional
    from src.config import DB_PATH
    from src.utils.config_manager import get_doc_folder

    if not os.path.exists(DB_PATH):
        logger.warning(f"Database path does not exist for backup: {DB_PATH}")
        return None

    # Determine backup folder
    doc_folder = get_doc_folder()
    if not doc_folder or not os.path.exists(doc_folder):
        doc_folder = os.path.dirname(os.path.abspath(DB_PATH))

    os.makedirs(doc_folder, exist_ok=True)
    today_str = datetime.now().strftime("%d-%m-%Y")
    backup_filename = f"DevDiary-{today_str}.db3"
    dest_path = os.path.join(doc_folder, backup_filename)

    # If the active DB is already the backup file itself, skip to avoid recursion
    if os.path.abspath(DB_PATH) == os.path.abspath(dest_path):
        logger.info("Active database is already the target backup file; skipping backup.")
        return dest_path

    try:
        # Use sqlite3 online backup API for safe transactional backup
        src_conn = sqlite3.connect(DB_PATH)
        dst_conn = sqlite3.connect(dest_path)
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        logger.info(f"Database backup created successfully: {dest_path}")
        return dest_path
    except Exception as e:
        logger.error(f"sqlite3 backup failed, falling back to file copy: {e}")
        try:
            shutil.copy2(DB_PATH, dest_path)
            logger.info(f"Database backup copied successfully: {dest_path}")
            return dest_path
        except Exception as copy_err:
            logger.error(f"Failed to create startup database backup: {copy_err}")
            return None


def remove_old_db_backups(max_days: int = 5):
    """
    Deletes backup files matching 'DevDiary-*' that are older than max_days.
    Matches C# DevDiaryManager.RemoveOldDBBackups().
    """
    import time
    from src.config import DB_PATH
    from src.utils.config_manager import get_doc_folder

    search_dirs = set()
    doc_folder = get_doc_folder()
    if doc_folder and os.path.exists(doc_folder):
        search_dirs.add(os.path.abspath(doc_folder))

    if os.path.exists(DB_PATH):
        search_dirs.add(os.path.abspath(os.path.dirname(DB_PATH)))

    active_db_abs = os.path.abspath(DB_PATH) if os.path.exists(DB_PATH) else None
    cutoff_time = time.time() - (max_days * 86400.0)

    for directory in search_dirs:
        try:
            for fname in os.listdir(directory):
                if not fname.startswith("DevDiary-"):
                    continue
                if not (fname.endswith(".db") or fname.endswith(".db3")):
                    continue
                fpath = os.path.join(directory, fname)
                abs_fpath = os.path.abspath(fpath)
                if abs_fpath == active_db_abs:
                    continue  # NEVER delete the active database!

                try:
                    file_mtime = os.path.getmtime(abs_fpath)
                    if file_mtime < cutoff_time:
                        os.remove(abs_fpath)
                        logger.info(f"Removed old database backup: {abs_fpath}")
                except Exception as del_err:
                    logger.warning(f"Could not remove old backup {abs_fpath}: {del_err}")
        except Exception as dir_err:
            logger.warning(f"Error scanning directory {directory} for old backups: {dir_err}")

