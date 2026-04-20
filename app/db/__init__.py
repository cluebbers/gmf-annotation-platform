"""Database initialization and session management."""

from collections.abc import Generator

from app.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative models."""
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get a database session.

    Yields:
        Session: A SQLAlchemy session instance.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize the database by creating all tables and applying fixes."""
    import app.db.tables  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_postgres_compatibility_fixes()


def _apply_postgres_compatibility_fixes() -> None:
    """Apply PostgreSQL-specific compatibility fixes to the database schema."""
    if engine.dialect.name != "postgresql":
        return

    statements = (
        """
        ALTER TABLE incidents
        ADD COLUMN IF NOT EXISTS is_gold_set BOOLEAN NOT NULL DEFAULT FALSE
        """,
        """
        ALTER TABLE model_runs
        ADD COLUMN IF NOT EXISTS provider VARCHAR NOT NULL DEFAULT 'openai'
        """,
        """
        ALTER TABLE model_runs
        ADD COLUMN IF NOT EXISTS temperature DOUBLE PRECISION NULL
        """,
        """
        ALTER TABLE model_runs
        ADD COLUMN IF NOT EXISTS max_completion_tokens INTEGER NULL
        """,
    )

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
