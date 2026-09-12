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
    """Initializes tables if not already present and seeds default data if brand new."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized/verified.")
    seed_default_data_if_empty()

