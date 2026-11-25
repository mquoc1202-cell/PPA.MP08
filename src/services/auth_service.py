from typing import Optional
from sqlalchemy.orm import Session
from src.core.logging import get_logger
from src.core.security import verify_password
from src.repositories.user_repo import UserRepository
from src.schemas.auth import UserSession

logger = get_logger("auth_service")


class AuthService:
    """Service handling user authentication and credential validation."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def authenticate(self, username: str, password: str) -> Optional[UserSession]:
        """Authenticate user by username and password, verifying account active status."""
        user = self.user_repo.get_by_username(username)
        if not user:
            logger.warning("Authentication failed: User '%s' does not exist.", username)
            return None

        if not user.is_active:
            logger.warning("Authentication failed: User '%s' is inactive / locked.", username)
            return None

        if not verify_password(password, user.password_hash):
            logger.warning("Authentication failed: Invalid password for user '%s'.", username)
            return None

        logger.info("User '%s' authenticated successfully with role '%s'.", user.username, user.role)
        return UserSession(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
        )
