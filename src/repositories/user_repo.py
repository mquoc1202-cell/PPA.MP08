from typing import Optional, List
from sqlalchemy.orm import Session
from src.models.user import User
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository handling User queries and database persistence."""

    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_username(self, username: str) -> Optional[User]:
        """Lookup active or inactive user by exact username."""
        return self.db.query(User).filter(User.username == username.strip()).first()

    def get_active_by_username(self, username: str) -> Optional[User]:
        """Lookup user by username only if account is active."""
        return (
            self.db.query(User)
            .filter(User.username == username.strip(), User.is_active.is_(True))
            .first()
        )
