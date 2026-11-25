import pytest
from typing import Generator
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

import src.models
from src.core.database import Base, get_db
from src.core.config import settings
from src.core.exceptions import register_exception_handlers
from src.core.logging import setup_logging
from src.core.security import hash_password
from src.models.user import User, UserRole

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
    """Creates a test FastAPI application with session middleware and test db session override."""
    from src.api.v1.api_router import api_router
    from src.web.dashboard import router as dashboard_router
    from src.web.admin_trucks import router as admin_trucks_router
    from src.web.admin_drivers import router as admin_drivers_router
    from src.web.trips import router as web_trips_router
    from src.web.schedule import router as web_schedule_router
    try:
        from src.web.auth import router as web_auth_router
    except ImportError:
        web_auth_router = None

    app = FastAPI(title="Freight Test App")
    
    # Session middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        session_cookie=settings.SESSION_COOKIE_NAME,
        max_age=settings.SESSION_MAX_AGE,
        same_site="lax",
    )
    register_exception_handlers(app)
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(dashboard_router)
    app.include_router(admin_trucks_router)
    app.include_router(admin_drivers_router)
    app.include_router(web_trips_router)
    app.include_router(web_schedule_router)
    if web_auth_router:
        app.include_router(web_auth_router)

    return app

@pytest.fixture
def client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """TestClient configured with dependency overrides."""
    with TestClient(test_app) as c:
        yield c

@pytest.fixture
def seed_test_users(db_session: Session):
    """Seed test users for unit and integration tests."""
    pwd_hash = hash_password("password123")
    dsp = User(username="dsp_test", password_hash=pwd_hash, full_name="DSP Test", role="DSP", is_active=True)
    sal = User(username="sal_test", password_hash=pwd_hash, full_name="SAL Test", role="SAL", is_active=True)
    mgr = User(username="mgr_test", password_hash=pwd_hash, full_name="MGR Test", role="MGR", is_active=True)
    inactive = User(username="inactive_test", password_hash=pwd_hash, full_name="Inactive Test", role="DSP", is_active=False)
    db_session.add_all([dsp, sal, mgr, inactive])
    db_session.flush()
    return {"dsp": dsp, "sal": sal, "mgr": mgr, "inactive": inactive}
