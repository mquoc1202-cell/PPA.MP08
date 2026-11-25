from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.models.trip import Trip, TripStatus
from src.models.trip_issue import TripIssue, IssueStatus
from src.repositories.base import BaseRepository


class TripRepository(BaseRepository[Trip]):
    """Repository handling Trip queries and persistence."""

    def __init__(self, db: Session):
        super().__init__(Trip, db)

    def get_by_reference_code(self, reference_code: str) -> Optional[Trip]:
        """Find trip by its unique reference code."""
        return self.db.query(Trip).filter(Trip.reference_code == reference_code.strip()).first()

    def filter_trips(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        has_issues: Optional[bool] = None,
        is_delayed: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Trip], int]:
        """Filter trips by status, text search, open issues, or operational delay, with pagination."""
        query = self.db.query(Trip)
        if status:
            query = query.filter(Trip.status == status)
        if is_delayed:
            query = query.filter(
                Trip.status.notin_([TripStatus.DELIVERED.value, TripStatus.COMPLETED.value, TripStatus.CANCELLED.value]),
                Trip.estimated_end_time.isnot(None),
                Trip.estimated_end_time < datetime.now(),
            )
        if has_issues:
            query = query.filter(
                Trip.issues.any(TripIssue.status == IssueStatus.OPEN.value)
            )
        if search:
            clean_search = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Trip.reference_code.ilike(clean_search),
                    Trip.sender_name.ilike(clean_search),
                    Trip.pickup_address.ilike(clean_search),
                    Trip.delivery_address.ilike(clean_search),
                    Trip.cargo_type.ilike(clean_search),
                )
            )
        total = query.count()
        items = query.order_by(Trip.id.desc()).offset(skip).limit(limit).all()
        return items, total

    def count_delayed_trips(self) -> int:
        """Count trips that have exceeded their estimated_end_time and are not yet completed/delivered/cancelled."""
        return (
            self.db.query(Trip)
            .filter(
                Trip.status.notin_([TripStatus.DELIVERED.value, TripStatus.COMPLETED.value, TripStatus.CANCELLED.value]),
                Trip.estimated_end_time.isnot(None),
                Trip.estimated_end_time < datetime.now(),
            )
            .count()
        )

    def count_trips_with_open_issues(self) -> int:
        """Count trips that currently have at least one unresolved issue."""
        return (
            self.db.query(Trip)
            .filter(Trip.issues.any(TripIssue.status == IssueStatus.OPEN.value))
            .count()
        )
