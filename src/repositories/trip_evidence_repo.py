from typing import List, Optional
from sqlalchemy.orm import Session
from src.models.trip_evidence import TripEvidence


class TripEvidenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_evidence(
        self,
        trip_id: int,
        file_path: str,
        file_name: str,
        file_size_bytes: int,
        mime_type: str,
        evidence_type: str = "POD",
        notes: Optional[str] = None,
        uploaded_by_user_id: Optional[int] = None,
    ) -> TripEvidence:
        """Create and persist a new evidence document."""
        evidence = TripEvidence(
            trip_id=trip_id,
            file_path=file_path,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            evidence_type=evidence_type,
            notes=notes,
            uploaded_by_user_id=uploaded_by_user_id,
        )
        self.db.add(evidence)
        self.db.flush()
        return evidence

    def get_evidence_by_trip(self, trip_id: int) -> List[TripEvidence]:
        """Fetch all evidence records for a given trip sorted by creation time."""
        return (
            self.db.query(TripEvidence)
            .filter(TripEvidence.trip_id == trip_id)
            .order_by(TripEvidence.created_at.asc())
            .all()
        )

    def get_by_id(self, evidence_id: int) -> Optional[TripEvidence]:
        """Fetch single evidence record by ID."""
        return self.db.query(TripEvidence).filter(TripEvidence.id == evidence_id).first()

    def count_by_trip(self, trip_id: int) -> int:
        """Count total evidence documents for a given trip."""
        return self.db.query(TripEvidence).filter(TripEvidence.id == trip_id).count()
