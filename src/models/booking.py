import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Index, CheckConstraint
from src.core.database import Base


class ResourceType(str, enum.Enum):
    TRUCK = "TRUCK"
    DRIVER = "DRIVER"


class BookingStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ServiceType(str, enum.Enum):
    FREIGHT = "FREIGHT"
    RENTAL = "RENTAL"


class ResourceBooking(Base):
    """
    SQLAlchemy Model for ResourceBooking.
    Canonical constraints cited from data-model.md:
    - ResourceBooking.resource_type: VARCHAR(20), NOT NULL
    - ResourceBooking.resource_id: INTEGER, NOT NULL, INDEX
    - ResourceBooking.reference_code: VARCHAR(50), NOT NULL, INDEX
    - ResourceBooking.service_type: VARCHAR(20), NOT NULL, DEFAULT 'FREIGHT', CHECK service_type IN ('FREIGHT', 'RENTAL')
    - ResourceBooking.start_time: DATETIME, NOT NULL
    - ResourceBooking.end_time: DATETIME, NOT NULL
    - ResourceBooking.status: VARCHAR(20), NOT NULL, DEFAULT 'CONFIRMED'
    """
    __tablename__ = "resource_bookings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    resource_type = Column(String(20), nullable=False)
    resource_id = Column(Integer, nullable=False, index=True)
    reference_code = Column(String(50), nullable=False, index=True)
    service_type = Column(
        String(20),
        CheckConstraint("service_type IN ('FREIGHT', 'RENTAL')", name="ck_booking_service_type_valid"),
        nullable=False,
        default=ServiceType.FREIGHT.value
    )
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default=BookingStatus.CONFIRMED.value)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_bookings_lookup", "resource_type", "resource_id", "status", "end_time"),
    )
