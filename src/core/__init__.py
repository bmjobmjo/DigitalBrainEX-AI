"""Core module initialization."""
from .database import get_db_session, get_engine, init_db
from .models import (
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
    TrackTempFileToDocConv,
    ClipboardHistory,
)
from .repository import DataRepository
from .crypto import (
    encrypt_des3,
    decrypt_des3,
    calc_md5_hash,
    verify_md5_hash,
    CryptoManager,
)
from .logger import setup_logger, logger
from .event_bus import event_bus

__all__ = [
    "get_db_session",
    "get_engine",
    "init_db",
    "Project",
    "Document",
    "DocumentCategory",
    "Url",
    "Task",
    "Secret",
    "TrackMe",
    "Goal",
    "WatchFolder",
    "Embedding",
    "TrackTempFileToDocConv",
    "ClipboardHistory",
    "DataRepository",
    "encrypt_des3",
    "decrypt_des3",
    "calc_md5_hash",
    "verify_md5_hash",
    "CryptoManager",
    "setup_logger",
    "logger",
    "event_bus",
]
