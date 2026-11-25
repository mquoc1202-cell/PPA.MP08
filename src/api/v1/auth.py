from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.security import get_current_user
from src.schemas.auth import (
    LoginRequest,
    UserSession,
    AuthResponse,
    UserProfileResponse,
    ActionResponse,
)
from src.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication API"])


@router.post("/login", response_model=AuthResponse)
def api_login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate user, set signed session cookie, and return user profile."""
    auth_service = AuthService(db)
    user_session = auth_service.authenticate(payload.username, payload.password)

    if not user_session:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "data": None,
                "error": "Tên đăng nhập hoặc mật khẩu không chính xác.",
                "meta": {},
            },
        )

    # Save to session cookie
    request.session["current_user"] = user_session.model_dump()

    return AuthResponse(
        success=True,
        data=user_session,
        error=None,
        meta={"message": "Đăng nhập thành công."},
    )


@router.post("/logout", response_model=ActionResponse)
def api_logout(request: Request):
    """Invalidate active session cookie."""
    request.session.clear()
    return ActionResponse(
        success=True,
        data={"message": "Đăng xuất thành công."},
        error=None,
        meta={},
    )


@router.get("/me", response_model=UserProfileResponse)
def api_get_current_user(current_user: UserSession = Depends(get_current_user)):
    """Retrieve profile of currently authenticated user."""
    return UserProfileResponse(
        success=True,
        data=current_user,
        error=None,
        meta={},
    )
