from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.models.trip_event import TripEvent
from src.repositories.base import BaseRepository


class TripEventRepository(BaseRepository[TripEvent]):
    """Repository handling immutable audit timeline events for trips."""

    def __init__(self, db: Session):
        super().__init__(TripEvent, db)

    def log_event(
        self,
        trip_id: int,
        event_type: str,
        from_status: str,
        to_status: str,
        actual_time: datetime,
        recorded_by_user_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> TripEvent:
        """Appends an immutable audit timeline event."""
        event = TripEvent(
            trip_id=trip_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            actual_time=actual_time,
            recorded_at=datetime.now(timezone.utc),
            recorded_by_user_id=recorded_by_user_id,
            notes=notes,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def get_events_for_trip(self, trip_id: int) -> List[TripEvent]:
        """Retrieves all chronological events for a trip."""
        return (
            self.db.query(TripEvent)
            .filter(TripEvent.trip_id == trip_id)
            .order_by(TripEvent.actual_time.asc(), TripEvent.id.asc())
            .all()
        )
