"""Database engine and session management."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import api.db.models  # noqa: F401 - ensure all tables are registered on Base.metadata
from api.config import settings
from api.db.base import Base
from api.db.seed import seed_categories

# Connect args (e.g. check_same_thread for SQLite in tests)
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 30

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

if settings.database_url.startswith("sqlite"):
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        cursor.close()

session_factory = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed."""
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables and seed baseline data."""
    Base.metadata.create_all(bind=engine)
    with session_factory() as db:
        seed_categories(db)
