from typing import List, Optional
from datetime import datetime, timezone, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from src.models.booking import ResourceBooking, BookingStatus, ResourceType
from src.repositories.base import BaseRepository


class ResourceBookingRepository(BaseRepository[ResourceBooking]):
    """Repository handling resource schedule collision queries and audit checks."""

    def __init__(self, db: Session):
        super().__init__(ResourceBooking, db)

    def has_booking_history(self, resource_type: str, resource_id: int) -> bool:
        """Checks if a truck or driver has ever participated in any booking (enforces Soft Delete Guard)."""
        count = self.db.query(ResourceBooking).filter(
            ResourceBooking.resource_type == resource_type,
            ResourceBooking.resource_id == resource_id,
        ).count()
        return count > 0

    def get_future_or_active_bookings(self, resource_type: str, resource_id: int) -> List[ResourceBooking]:
        """Retrieves bookings that are either currently active or scheduled in the future."""
        now = datetime.now(timezone.utc)
        return self.db.query(ResourceBooking).filter(
            ResourceBooking.resource_type == resource_type,
            ResourceBooking.resource_id == resource_id,
            ResourceBooking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.IN_PROGRESS.value]),
            ResourceBooking.end_time >= now,
        ).all()

    def get_overlapping_bookings(
        self,
        resource_type: str,
        resource_id: int,
        start_time: datetime,
        end_time: datetime,
        exclude_reference_code: Optional[str] = None,
    ) -> List[ResourceBooking]:
        """
        Checks if the resource has any overlapping confirmed/in_progress bookings within [start_time, end_time].
        Formula: existing.start_time < new_end_time AND existing.end_time > new_start_time.
        Optional exclude_reference_code allows safe re-assignment of the same trip.
        """
        query = self.db.query(ResourceBooking).filter(
            ResourceBooking.resource_type == resource_type,
            ResourceBooking.resource_id == resource_id,
            ResourceBooking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.IN_PROGRESS.value]),
            and_(
                ResourceBooking.start_time < end_time,
                ResourceBooking.end_time > start_time,
            ),
        )
        if exclude_reference_code:
            query = query.filter(ResourceBooking.reference_code != exclude_reference_code)
        return query.all()

    def get_bookings_by_range(
        self,
        resource_type: str,
        resource_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[ResourceBooking]:
        """Retrieves all bookings for a given resource within a date range."""
        query = self.db.query(ResourceBooking).filter(
            ResourceBooking.resource_type == resource_type,
            ResourceBooking.resource_id == resource_id,
            ResourceBooking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.IN_PROGRESS.value]),
        )
        if start_date:
            start_dt = datetime.combine(start_date, datetime.min.time())
            query = query.filter(ResourceBooking.end_time >= start_dt)
        if end_date:
            end_dt = datetime.combine(end_date, datetime.max.time())
            query = query.filter(ResourceBooking.start_time <= end_dt)
        return query.order_by(ResourceBooking.start_time.asc()).all()

    def cancel_bookings_by_reference(self, reference_code: str) -> int:
        """Mark all active bookings for a reference code as CANCELLED."""
        bookings = self.db.query(ResourceBooking).filter(
            ResourceBooking.reference_code == reference_code,
            ResourceBooking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.IN_PROGRESS.value]),
        ).all()
        for b in bookings:
            b.status = BookingStatus.CANCELLED.value
        self.db.commit()
        return len(bookings)

    def transition_bookings_status(
        self, reference_code: str, from_status: str, to_status: str
    ) -> int:
        """Transitions status of bookings with a reference code (e.g. CONFIRMED -> IN_PROGRESS)."""
        bookings = self.db.query(ResourceBooking).filter(
            ResourceBooking.reference_code == reference_code,
            ResourceBooking.status == from_status,
        ).all()
        for b in bookings:
            b.status = to_status
        return len(bookings)

    def complete_bookings_for_trip(
        self, reference_code: str, completed_time: datetime
    ) -> int:
        """Transitions bookings for a trip to COMPLETED and sets actual end_time."""
        bookings = self.db.query(ResourceBooking).filter(
            ResourceBooking.reference_code == reference_code,
            ResourceBooking.status.in_([BookingStatus.IN_PROGRESS.value, BookingStatus.CONFIRMED.value]),
        ).all()
        for b in bookings:
            b.status = BookingStatus.COMPLETED.value
            b.end_time = completed_time
        return len(bookings)

    def has_in_progress_booking(
        self, resource_type: str, resource_id: int, exclude_reference_code: Optional[str] = None
    ) -> bool:
        """Checks if a resource is currently busy with another in-progress booking (BR-09)."""
        query = self.db.query(ResourceBooking).filter(
            ResourceBooking.resource_type == resource_type,
            ResourceBooking.resource_id == resource_id,
            ResourceBooking.status == BookingStatus.IN_PROGRESS.value,
        )
        if exclude_reference_code:
            query = query.filter(ResourceBooking.reference_code != exclude_reference_code)
        return query.count() > 0

    def extend_booking_end_time(
        self, reference_code: str, new_end_time: datetime
    ) -> int:
        """Updates end_time for active bookings of a trip to reflect rescheduled completion."""
        bookings = self.db.query(ResourceBooking).filter(
            ResourceBooking.reference_code == reference_code,
            ResourceBooking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.IN_PROGRESS.value]),
        ).all()
        for b in bookings:
            b.end_time = new_end_time
        self.db.flush()
        return len(bookings)

    def find_future_conflicts_for_resources(
        self,
        exclude_reference_code: str,
        truck_id: Optional[int],
        driver_id: Optional[int],
        start_time: datetime,
        end_time: datetime,
    ) -> List[ResourceBooking]:
        """
        Finds overlapping bookings for given truck or driver in [start_time, end_time],
        excluding the current trip's reference_code. Covers both FREIGHT and RENTAL services.
        """
        conditions = []
        if truck_id:
            conditions.append(
                and_(
                    ResourceBooking.resource_type == ResourceType.TRUCK.value,
                    ResourceBooking.resource_id == truck_id,
                )
            )
        if driver_id:
            conditions.append(
                and_(
                    ResourceBooking.resource_type == ResourceType.DRIVER.value,
                    ResourceBooking.resource_id == driver_id,
                )
            )

        if not conditions:
            return []

        query = self.db.query(ResourceBooking).filter(
            ResourceBooking.reference_code != exclude_reference_code,
            ResourceBooking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.IN_PROGRESS.value]),
            or_(*conditions),
            and_(
                ResourceBooking.start_time < end_time,
                ResourceBooking.end_time > start_time,
            ),
        )
        return query.all()
