"""PostgreSQL database connection and session management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from .config import settings
from .logger import get_logger

logger = get_logger(__name__)

# SQLAlchemy Base for ORM models
Base = declarative_base()

# Engine configuration
# Using NullPool for async thread pool compatibility
# This prevents prepared statement errors when using asyncio.run_in_executor()
engine = create_engine(
    settings.database_url,
    poolclass=NullPool,  # Disable connection pooling for thread pool compatibility
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.debug,  # Log SQL queries in debug mode
    connect_args={"prepared_statement_cache_size": 0},  # Disable prepared statements
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Get database session (FastAPI dependency).

    Yields:
        SQLAlchemy session

    Example:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Get database session as context manager (for workers/scripts).

    Example:
        with get_db_context() as db:
            items = db.query(Item).all()
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
    """Initialize database (create all tables)."""
    logger.info("Initializing database schema")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully")


def check_db_connection() -> bool:
    """Check if database connection is healthy."""
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
