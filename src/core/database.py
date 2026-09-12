"""
Database Connection and Session Management for DigitalBrainEX AI.
Connects directly to the existing SQLite database via SQLAlchemy 2.0.
"""
from contextlib import contextmanager
from typing import Generator
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


def init_db():
    """Initializes tables if not already present."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized/verified.")
