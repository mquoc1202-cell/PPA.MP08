from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.templates import templates
from src.core.security import get_current_user_optional
from src.services.auth_service import AuthService

router = APIRouter(tags=["Auth Web"])


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    next: Optional[str] = None,
    logged_out: Optional[bool] = None,
):
    """Render Login Page."""
    # If already logged in, redirect to dashboard or next url
    current_user = get_current_user_optional(request)
    if current_user:
        target = next if next and next.startswith("/") else "/dashboard"
        return RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "next_url": next or "/dashboard",
            "logged_out": logged_out,
            "error_message": None,
            "username": "",
            "current_user": None,
        },
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next_url: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Process Login form submission."""
    auth_service = AuthService(db)
    user_session = auth_service.authenticate(username, password)

    if not user_session:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "next_url": next_url or "/dashboard",
                "logged_out": False,
                "error_message": "Tên đăng nhập hoặc mật khẩu không chính xác.",
                "username": username,
                "current_user": None,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Establish session
    request.session["current_user"] = user_session.model_dump()
    target = next_url if next_url and next_url.startswith("/") else "/dashboard"
    return RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
def logout_view(request: Request):
    """Clear session and redirect to login page."""
    request.session.clear()
    return RedirectResponse(url="/login?logged_out=true", status_code=status.HTTP_303_SEE_OTHER)
