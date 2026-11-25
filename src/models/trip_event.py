import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base


class TripEventType(str, enum.Enum):
    PICKUP_CONFIRMED = "PICKUP_CONFIRMED"
    DEPARTURE_CONFIRMED = "DEPARTURE_CONFIRMED"
    DELIVERY_CONFIRMED = "DELIVERY_CONFIRMED"
    DELIVERY_FAILED = "DELIVERY_FAILED"
    TRIP_COMPLETED = "TRIP_COMPLETED"
    ISSUE_LOGGED = "ISSUE_LOGGED"
    ISSUE_RESOLVED = "ISSUE_RESOLVED"
    SCHEDULE_DELAYED = "SCHEDULE_DELAYED"


class TripEvent(Base):
    """
    SQLAlchemy Model for TripEvent (Dòng thời gian sự kiện mốc chuyến hàng).
    Canonical constraints cited from data-model.md:
    - TripEvent.trip_id: INTEGER, NOT NULL, FOREIGN KEY (trips.id) ON DELETE CASCADE, INDEX
    - TripEvent.event_type: VARCHAR(50), NOT NULL
    - TripEvent.from_status: VARCHAR(20), NOT NULL
    - TripEvent.to_status: VARCHAR(20), NOT NULL
    - TripEvent.actual_time: DATETIME, NOT NULL
    - TripEvent.recorded_at: DATETIME, NOT NULL, DEFAULT UTC NOW
    - TripEvent.recorded_by_user_id: INTEGER, NULLABLE, FOREIGN KEY (users.id)
    - TripEvent.notes: VARCHAR(500), NULLABLE
    """
    __tablename__ = "trip_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    from_status = Column(String(20), nullable=False)
    to_status = Column(String(20), nullable=False)
    actual_time = Column(DateTime, nullable=False)
    recorded_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(String(500), nullable=True)

    trip = relationship("Trip", back_populates="events")
    user = relationship("User")
