import os
import sys
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure test settings are active
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "True"
os.environ["ALLOW_SQLITE_FALLBACK"] = "True"

from app.database import Base, get_db
from app.main import app

# In-memory SQLite engine for fast, isolated unit test execution
TEST_SQLITE_URL = "sqlite:///:memory:"
test_sqlite_engine = create_engine(
    TEST_SQLITE_URL,
    connect_args={"check_same_thread": False}
)

@event.listens_for(test_sqlite_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_sqlite_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all tables in memory once for test session."""
    Base.metadata.create_all(bind=test_sqlite_engine)
    yield
    Base.metadata.drop_all(bind=test_sqlite_engine)


@pytest.fixture
def db():
    """Provides a transactional database session that rolls back after each test."""
    connection = test_sqlite_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def postgres_engine():
    """
    Attempts to connect to PostgreSQL for canonical integration tests.
    If PostgreSQL is unavailable, yields None so tests report skipping explicitly.
    """
    pg_url = os.environ.get(
        "POSTGRES_TEST_DATABASE_URL",
        "postgresql+psycopg://kanakku:kanakku_secret_123@localhost:5432/kanakku_prod"
    )
    try:
        engine = create_engine(pg_url, connect_args={"connect_timeout": 2}, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception:
        return None
