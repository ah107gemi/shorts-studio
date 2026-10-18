"""
SQLAlchemy database setup for Shorts Studio.
Provides engine, session factory, declarative base, and initialization helpers.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


# SQLite requires check_same_thread=False when used with FastAPI's
# threaded request handling.
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create all tables defined by models that inherit from Base.
    Safe to call multiple times – existing tables are not recreated.
    """
    # Ensure the data directory exists so SQLite can create its file.
    settings.ensure_directories()

    # Import models so they are registered on Base.metadata before create_all.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
