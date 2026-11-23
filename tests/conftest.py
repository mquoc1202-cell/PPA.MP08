import pytest
from typing import Generator
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.core.database import Base, get_db
from src.core.exceptions import register_exception_handlers
from src.core.logging import setup_logging

# Configure logging for tests
setup_logging("DEBUG")

# Create in-memory SQLite engine for fast, isolated tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables at start and drop at end."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provides a fresh database session per test with rollback on cleanup."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def test_app(db_session: Session) -> FastAPI:
    """Creates a test FastAPI application with the test db session override."""
    from src.api.v1.api_router import api_router
    app = FastAPI(title="Freight Test App")
    register_exception_handlers(app)
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.include_router(api_router, prefix="/api/v1")
    return app

@pytest.fixture
def client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """TestClient configured with dependency overrides."""
    with TestClient(test_app) as c:
        yield c
