import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, CheckConstraint
from src.core.database import Base


class UserRole(str, enum.Enum):
    DSP = "DSP"   # Dispatcher - Điều phối viên
    SAL = "SAL"   # Sales - Nhân viên kinh doanh (Chỉ đọc)
    MGR = "MGR"   # Manager - Quản lý / Giám đốc


class User(Base):
    """
    SQLAlchemy Model for User.
    Canonical constraints cited from data-model.md:
    - User.username: VARCHAR(50), NOT NULL, UNIQUE, INDEX, length >= 3
    - User.password_hash: VARCHAR(255), NOT NULL
    - User.full_name: VARCHAR(100), NOT NULL
    - User.role: VARCHAR(20), NOT NULL, DEFAULT 'DSP', CHECK role IN ('DSP', 'SAL', 'MGR')
    - User.is_active: BOOLEAN, NOT NULL, DEFAULT TRUE
    """
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('DSP', 'SAL', 'MGR')", name="ck_user_role_valid"),
        CheckConstraint("length(username) >= 3", name="ck_username_length"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.DSP.value)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
