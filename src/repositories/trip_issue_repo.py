from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.models.trip_issue import TripIssue, IssueStatus


class TripIssueRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_issue(
        self,
        trip_id: int,
        issue_type: str,
        description: str,
        occurred_at: Optional[datetime] = None,
        handled_by: Optional[str] = None,
        estimated_resolution_time: Optional[datetime] = None,
        reported_by_user_id: Optional[int] = None,
        status: str = IssueStatus.OPEN.value,
    ) -> TripIssue:
        """Create and persist a new trip incident/issue."""
        issue = TripIssue(
            trip_id=trip_id,
            issue_type=issue_type,
            description=description,
            occurred_at=occurred_at or datetime.now(timezone.utc),
            handled_by=handled_by,
            estimated_resolution_time=estimated_resolution_time,
            reported_by_user_id=reported_by_user_id,
            status=status,
        )
        self.db.add(issue)
        self.db.flush()
        return issue

    def get_issues_by_trip(self, trip_id: int) -> List[TripIssue]:
        """Fetch all issues for a given trip sorted by creation time descending."""
        return (
            self.db.query(TripIssue)
            .filter(TripIssue.trip_id == trip_id)
            .order_by(TripIssue.created_at.desc())
            .all()
        )

    def get_open_issues_by_trip(self, trip_id: int) -> List[TripIssue]:
        """Fetch unresolved issues for a trip."""
        return (
            self.db.query(TripIssue)
            .filter(TripIssue.trip_id == trip_id, TripIssue.status == IssueStatus.OPEN.value)
            .order_by(TripIssue.created_at.desc())
            .all()
        )

    def get_open_issues_count(self, trip_id: Optional[int] = None) -> int:
        """Count open unresolved issues."""
        query = self.db.query(TripIssue).filter(TripIssue.status == IssueStatus.OPEN.value)
        if trip_id is not None:
            query = query.filter(TripIssue.trip_id == trip_id)
        return query.count()

    def resolve_issue(self, issue_id: int, resolution_notes: Optional[str] = None) -> Optional[TripIssue]:
        """Mark an issue as resolved with resolution notes."""
        issue = self.db.query(TripIssue).filter(TripIssue.id == issue_id).first()
        if issue:
            issue.status = IssueStatus.RESOLVED.value
            if resolution_notes:
                issue.resolution_notes = resolution_notes
            issue.resolved_at = datetime.now(timezone.utc)
            self.db.flush()
        return issue
