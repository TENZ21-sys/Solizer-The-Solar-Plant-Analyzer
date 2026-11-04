"""
SoliZer Intelligence Platform - Database Connection & Session Management.

Configures the SQLAlchemy engine, session factory, and declarative Base
for the SoliZer SQLite database. The database file is stored at
``./data/solizer.db`` relative to the application's working directory.

Usage::

    from app.db.database import get_db, engine, Base

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Use a session
    with get_db() as db:
        ...
"""

import os
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    sessionmaker,
)

# ---------------------------------------------------------------------------
# Database path – stored under ./data/ relative to the working directory
# ---------------------------------------------------------------------------
_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Solizer", "data")
os.makedirs(_DATA_DIR, exist_ok=True)

db_path = os.path.join(_DATA_DIR, 'solizer.db').replace("\\", "/")
DATABASE_URL = f"sqlite:///{db_path}"

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},  # Required for SQLite + threads
    pool_pre_ping=True,
)


# Enable SQLite foreign-key enforcement (off by default in SQLite)
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001
    """Turn on foreign-key constraint enforcement for every connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Declarative Base (SQLAlchemy 2.0 style)
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Application-wide declarative base for all ORM models."""

    pass


# ---------------------------------------------------------------------------
# Dependency / context-manager helpers
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """Yield a transactional database session that auto-closes.

    Compatible with FastAPI's ``Depends()`` injection as well as manual use::

        # FastAPI route
        def my_route(db: Session = Depends(get_db)):
            ...

        # Manual use
        gen = get_db()
        db = next(gen)
        try:
            ...
        finally:
            gen.close()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create all tables defined by ORM models if they don't exist yet.

    This import of ``models`` triggers SQLAlchemy to register every table
    on ``Base.metadata`` before ``create_all`` is called.
    """
    import app.db.models  # noqa: F401 – register models

    Base.metadata.create_all(bind=engine)
