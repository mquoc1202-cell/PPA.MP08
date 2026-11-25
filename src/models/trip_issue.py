import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base


class IssueStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class TripIssue(Base):
    """
    SQLAlchemy Model for TripIssue (Nhật ký Sự cố Chuyến Hàng).
    Canonical constraints cited from data-model.md:
    - TripIssue.trip_id: INTEGER, NOT NULL, FOREIGN KEY (trips.id) ON DELETE CASCADE, INDEX
    - TripIssue.issue_type: VARCHAR(50), NOT NULL
    - TripIssue.description: VARCHAR(1000), NOT NULL
    - TripIssue.status: VARCHAR(20), NOT NULL, DEFAULT 'OPEN'
    - TripIssue.reported_by_user_id: INTEGER, NULLABLE, FOREIGN KEY (users.id)
    - TripIssue.created_at: DATETIME, NOT NULL, DEFAULT UTC NOW
    - TripIssue.resolved_at: DATETIME, NULLABLE
    """
    __tablename__ = "trip_issues"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    issue_type = Column(String(50), nullable=False)
    description = Column(String(1000), nullable=False)
    status = Column(String(20), nullable=False, default=IssueStatus.OPEN.value)
    occurred_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    handled_by = Column(String(150), nullable=True)
    estimated_resolution_time = Column(DateTime, nullable=True)
    resolution_notes = Column(String(1000), nullable=True)
    reported_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)

    trip = relationship("Trip", back_populates="issues")
    reported_by = relationship("User")
