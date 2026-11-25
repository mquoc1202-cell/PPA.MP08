import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.core.security import hash_password, verify_password
from src.services.auth_service import AuthService
from src.schemas.auth import LoginRequest
from src.models.user import User


def test_password_hashing():
    """Verify bcrypt password hashing and verification functions."""
    plain = "SuperSecret123!"
    hashed = hash_password(plain)

    assert hashed != plain
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False


def test_auth_service_success(db_session: Session, seed_test_users):
    """AuthService authenticates valid active user."""
    auth_service = AuthService(db_session)
    user_session = auth_service.authenticate("dsp_test", "password123")

    assert user_session is not None
    assert user_session.username == "dsp_test"
    assert user_session.role == "DSP"
    assert user_session.full_name == "DSP Test"


def test_auth_service_invalid_credentials(db_session: Session, seed_test_users):
    """AuthService rejects wrong password and non-existent user."""
    auth_service = AuthService(db_session)

    # Wrong password
    assert auth_service.authenticate("dsp_test", "incorrect_pwd") is None

    # Non-existent user
    assert auth_service.authenticate("non_existent", "password123") is None


def test_auth_service_inactive_user(db_session: Session, seed_test_users):
    """AuthService rejects locked or inactive accounts."""
    auth_service = AuthService(db_session)
    assert auth_service.authenticate("inactive_test", "password123") is None


def test_api_auth_lifecycle(client: TestClient, db_session: Session, seed_test_users):
    """Contract & functional test for /api/v1/auth/login, /me, and /logout."""
    # 1. Initially unauthenticated /me -> 401
    resp_me = client.get("/api/v1/auth/me")
    assert resp_me.status_code == 401

    # 2. Login with wrong password -> 400
    resp_fail = client.post(
        "/api/v1/auth/login",
        json={"username": "dsp_test", "password": "wrongpassword"}
    )
    assert resp_fail.status_code == 400
    assert resp_fail.json()["success"] is False

    # 3. Login with valid credentials -> 200
    resp_login = client.post(
        "/api/v1/auth/login",
        json={"username": "dsp_test", "password": "password123"}
    )
    assert resp_login.status_code == 200
    data = resp_login.json()
    assert data["success"] is True
    assert data["data"]["username"] == "dsp_test"
    assert data["data"]["role"] == "DSP"

    # 4. Now authenticated /me -> 200
    resp_me_auth = client.get("/api/v1/auth/me")
    assert resp_me_auth.status_code == 200
    assert resp_me_auth.json()["data"]["username"] == "dsp_test"

    # 5. Logout -> 200
    resp_logout = client.post("/api/v1/auth/logout")
    assert resp_logout.status_code == 200

    # 6. /me after logout -> 401
    resp_me_after = client.get("/api/v1/auth/me")
    assert resp_me_after.status_code == 401


def test_web_auth_lifecycle(client: TestClient, db_session: Session, seed_test_users):
    """Test web HTML login view, form submission, and web logout."""
    # 1. GET /login returns 200
    resp_page = client.get("/login")
    assert resp_page.status_code == 200
    assert "Đăng Nhập" in resp_page.text

    # 2. POST /login with invalid credentials returns 400 with error message
    resp_bad = client.post(
        "/login",
        data={"username": "dsp_test", "password": "wrong_password"}
    )
    assert resp_bad.status_code == 400
    assert "không chính xác" in resp_bad.text

    # 3. POST /login with valid credentials redirects 303 to /dashboard
    resp_ok = client.post(
        "/login",
        data={"username": "dsp_test", "password": "password123"},
        follow_redirects=False
    )
    assert resp_ok.status_code == 303
    assert resp_ok.headers["location"] == "/dashboard"

    # 4. GET /logout clears session and redirects to /login?logged_out=true
    resp_logout = client.get("/logout", follow_redirects=False)
    assert resp_logout.status_code == 303
    assert "/login" in resp_logout.headers["location"]
