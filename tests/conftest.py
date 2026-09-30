"""Global pytest configuration and database fixtures for DataGuard AI test suite."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app

# Shared in-memory SQLite database utilizing StaticPool so all sessions share the in-memory database
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """FastAPI dependency override providing isolated test database sessions."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override application database dependency globally for all test clients
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_test_database():
    """Ensure clean database schema exists for each test case."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
