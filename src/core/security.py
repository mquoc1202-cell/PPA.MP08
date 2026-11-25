import bcrypt
from typing import List, Optional, Callable
from fastapi import Request, HTTPException, status, Depends
from src.core.logging import get_logger
from src.schemas.auth import UserSession

logger = get_logger("security")


class AuthenticationRequiredError(Exception):
    """Raised when an unauthenticated request attempts to access a protected resource."""
    def __init__(self, next_url: str = "/dashboard"):
        self.next_url = next_url
        super().__init__("Vui lòng đăng nhập để tiếp tục.")


class PermissionDeniedError(Exception):
    """Raised when an authenticated user lacks required roles."""
    def __init__(self, message: str = "Bạn không có quyền thực hiện thao tác này."):
        self.message = message
        super().__init__(self.message)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.warning("Password verification failed with exception: %s", e)
        return False


def get_current_user_optional(request: Request) -> Optional[UserSession]:
    """Retrieve currently authenticated user session if present, else None."""
    user_dict = request.session.get("current_user")
    if not user_dict or not isinstance(user_dict, dict):
        return None
    try:
        return UserSession(**user_dict)
    except Exception as e:
        logger.warning("Invalid session user format, clearing: %s", e)
        request.session.pop("current_user", None)
        return None


def get_current_user(request: Request) -> UserSession:
    """Enforce active authentication session."""
    user = get_current_user_optional(request)
    if user is not None:
        return user

    # Not authenticated: determine whether API or Web request
    is_api = request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", "")
    if is_api:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vui lòng đăng nhập để tiếp tục."
        )
    raise AuthenticationRequiredError(next_url=str(request.url.path))


def require_role(allowed_roles: List[str]) -> Callable:
    """Factory creating dependency to enforce RBAC permissions."""
    def role_checker(request: Request, user: UserSession = Depends(get_current_user)) -> UserSession:
        if user.role not in allowed_roles:
            logger.warning(
                "Access denied for user '%s' (role: %s) on path %s. Allowed: %s",
                user.username,
                user.role,
                request.url.path,
                allowed_roles,
            )
            is_api = request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", "")
            if is_api:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền thực hiện thao tác này."
                )
            raise PermissionDeniedError(message="Bạn không có quyền thực hiện thao tác này.")
        return user

    return role_checker
