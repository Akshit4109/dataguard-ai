"""Database engine, session management, and base models for DataGuard AI."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Base class for all SQLAlchemy declarative models
Base = declarative_base()


def get_database_url() -> str:
    """Retrieve database connection string, defaulting to local SQLite if not configured."""
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    return "sqlite:///./data/dataguard.db"


def create_db_engine(db_url: str):
    """Create a configured SQLAlchemy engine compatible with PostgreSQL and SQLite."""
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return create_engine(db_url, connect_args=connect_args)

    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


# Initialize global engine and session factory
db_url = get_database_url()
engine = create_db_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session with safe transaction lifecycle."""
    db = SessionLocal()
    try:
        yield db
    except Exception as err:
        db.rollback()
        logger.error("Database transaction rolled back due to error: %s", err)
        raise
    finally:
        db.close()


def init_db(target_engine=None) -> None:
    """Initialize database tables using SQLAlchemy declarative metadata."""
    active_engine = target_engine or engine
    try:
        import app.models  # noqa: F401
        Base.metadata.create_all(bind=active_engine)
        logger.info("Database tables initialized successfully on: %s", active_engine.url.drivername)
    except Exception as err:
        logger.warning("Could not automatically initialize database tables: %s", err)


# Ensure tables exist on local startup
init_db(engine)
