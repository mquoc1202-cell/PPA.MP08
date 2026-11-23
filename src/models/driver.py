import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from src.core.database import Base

class DriverStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class Driver(Base):
    """
    SQLAlchemy Model for Driver.
    Canonical constraints cited from data-model.md:
    - Driver.driver_code: VARCHAR(20), NOT NULL, UNIQUE, INDEX
    - Driver.full_name: VARCHAR(100), NOT NULL
    - Driver.phone_number: VARCHAR(20), NOT NULL
    - Driver.status: VARCHAR(20), NOT NULL, DEFAULT 'ACTIVE'
    """
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    driver_code = Column(String(20), nullable=False, unique=True, index=True)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default=DriverStatus.ACTIVE.value)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
