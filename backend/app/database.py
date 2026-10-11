import logging
from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

logger = logging.getLogger(__name__)

# Base model for all declarative entities
Base = declarative_base()


def get_engine():
    db_url = settings.DATABASE_URL
    is_sqlite = db_url.startswith("sqlite")

    connect_args = {}
    if is_sqlite:
        connect_args["check_same_thread"] = False
    else:
        connect_args["connect_timeout"] = 2

    try:
        engine = create_engine(
            db_url,
            connect_args=connect_args,
            pool_pre_ping=True,
            echo=False
        )
        # Attempt quick test connection if not sqlite
        if not is_sqlite:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        return engine, False
    except Exception as e:
        if not settings.ALLOW_SQLITE_FALLBACK and not is_sqlite:
            logger.error(f"Cannot connect to primary PostgreSQL database ({db_url}) and ALLOW_SQLITE_FALLBACK is False: {e}")
            raise RuntimeError(
                f"Failed to connect to canonical PostgreSQL database at {db_url} and ALLOW_SQLITE_FALLBACK is disabled. "
                f"To allow local offline SQLite fallback, set ALLOW_SQLITE_FALLBACK=True. Original error: {e}"
            )
        logger.warning(
            f"Could not connect to canonical database ({db_url}): {e}. "
            f"Falling back to local development SQLite database ({settings.SQLITE_DEV_FALLBACK_URL})."
        )
        sqlite_engine = create_engine(
            settings.SQLITE_DEV_FALLBACK_URL,
            connect_args={"check_same_thread": False},
            echo=False
        )
        return sqlite_engine, True


engine, is_fallback_sqlite = get_engine()

# If using SQLite, strictly enforce relational foreign keys
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    # Check if this connection is sqlite
    if "sqlite" in str(type(dbapi_connection)).lower():
        cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "dialect": engine.dialect.name,
            "is_fallback": is_fallback_sqlite,
            "url_safe": engine.url.render_as_string(hide_password=True)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "dialect": engine.dialect.name,
            "is_fallback": is_fallback_sqlite
        }
