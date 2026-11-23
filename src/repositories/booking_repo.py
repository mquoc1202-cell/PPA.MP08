from typing import List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from src.models.booking import ResourceBooking, BookingStatus
from src.repositories.base import BaseRepository

class ResourceBookingRepository(BaseRepository[ResourceBooking]):
    """Repository handling resource schedule collision queries and audit checks."""

    def __init__(self, db: Session):
        super().__init__(ResourceBooking, db)

    def has_booking_history(self, resource_type: str, resource_id: int) -> bool:
        """Checks if a truck or driver has ever participated in any booking (enforces Soft Delete Guard)."""
        count = self.db.query(ResourceBooking).filter(
            ResourceBooking.resource_type == resource_type,
            ResourceBooking.resource_id == resource_id
        ).count()
        return count > 0

    def get_future_or_active_bookings(self, resource_type: str, resource_id: int) -> List[ResourceBooking]:
        """Retrieves bookings that are either currently active or scheduled in the future."""
        now = datetime.now(timezone.utc)
        return self.db.query(ResourceBooking).filter(
            ResourceBooking.resource_type == resource_type,
            ResourceBooking.resource_id == resource_id,
            ResourceBooking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.IN_PROGRESS.value]),
            ResourceBooking.end_time >= now
        ).all()

    def get_overlapping_bookings(
        self, resource_type: str, resource_id: int, start_time: datetime, end_time: datetime
    ) -> List[ResourceBooking]:
        """Checks if the resource has any overlapping confirmed/in_progress bookings within [start_time, end_time]."""
        return self.db.query(ResourceBooking).filter(
            ResourceBooking.resource_type == resource_type,
            ResourceBooking.resource_id == resource_id,
            ResourceBooking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.IN_PROGRESS.value]),
            and_(
                ResourceBooking.start_time < end_time,
                ResourceBooking.end_time > start_time
            )
        ).all()
