import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, CheckConstraint
from src.core.database import Base

class TruckStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    INACTIVE = "INACTIVE"

class Truck(Base):
    """
    SQLAlchemy Model for Truck.
    Canonical constraints cited from data-model.md:
    - Truck.plate_number: VARCHAR(20), NOT NULL
    - Truck.normalized_plate: VARCHAR(20), NOT NULL, UNIQUE, INDEX
    - Truck.truck_type: VARCHAR(50), NOT NULL
    - Truck.capacity_kg: INTEGER, NOT NULL, CHECK (capacity_kg > 0)
    - Truck.status: VARCHAR(20), NOT NULL, DEFAULT 'ACTIVE'
    """
    __tablename__ = "trucks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    plate_number = Column(String(20), nullable=False)
    normalized_plate = Column(String(20), nullable=False, unique=True, index=True)
    truck_type = Column(String(50), nullable=False)
    capacity_kg = Column(
        Integer,
        CheckConstraint("capacity_kg > 0", name="ck_truck_capacity_positive"),
        nullable=False
    )
    description = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default=TruckStatus.ACTIVE.value)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
