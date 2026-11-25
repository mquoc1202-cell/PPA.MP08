from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base


class TripEvidence(Base):
    """
    SQLAlchemy Model for TripEvidence (Chứng từ và Bằng chứng bàn giao - POD).
    Canonical constraints cited from data-model.md:
    - TripEvidence.trip_id: INTEGER, NOT NULL, FOREIGN KEY (trips.id) ON DELETE CASCADE, INDEX
    - TripEvidence.file_path: VARCHAR(500), NOT NULL
    - TripEvidence.file_name: VARCHAR(255), NOT NULL
    - TripEvidence.file_size_bytes: INTEGER, NOT NULL
    - TripEvidence.mime_type: VARCHAR(100), NOT NULL
    - TripEvidence.evidence_type: VARCHAR(50), NOT NULL, DEFAULT 'POD'
    - TripEvidence.notes: VARCHAR(500), NULLABLE
    - TripEvidence.uploaded_by_user_id: INTEGER, NULLABLE, FOREIGN KEY (users.id)
    - TripEvidence.created_at: DATETIME, NOT NULL, DEFAULT UTC NOW
    """
    __tablename__ = "trip_evidence"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    evidence_type = Column(String(50), nullable=False, default="POD")
    notes = Column(String(500), nullable=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    trip = relationship("Trip", back_populates="evidence")
    uploaded_by = relationship("User")
