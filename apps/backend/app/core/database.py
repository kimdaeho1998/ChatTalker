from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import get_settings


def get_development_engine() -> Engine | None:
    """Create a TLS-only, bounded engine when an explicit development URL exists."""
    settings = get_settings()
    database_url = settings.database_url
    if database_url is None:
        return None
    if database_url.startswith("postgres://"):
        database_url = "postgresql+psycopg://" + database_url.removeprefix("postgres://")
    elif database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    if not database_url.startswith("postgresql+psycopg://"):
        raise ValueError("DATABASE_URL must use the postgresql+psycopg driver")
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
        pool_timeout=10,
        connect_args={"sslmode": settings.database_sslmode},
    )
