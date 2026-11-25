from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.core.logging import get_logger
from src.core.exceptions import NotFoundException, BusinessRuleException, ScheduleConflictException
from src.models.trip import Trip, TripStatus
from src.models.trip_issue import TripIssue, IssueStatus
from src.models.trip_event import TripEvent, TripEventType
from src.models.booking import ResourceBooking
from src.repositories.trip_repo import TripRepository
from src.repositories.trip_issue_repo import TripIssueRepository
from src.repositories.booking_repo import ResourceBookingRepository
from src.schemas.trip import CreateTripIssueRequest, ResolveTripIssueRequest

logger = get_logger("incident_service")


class IncidentService:
    """Service handling incident logging, resolution, and operational delay reschedule workflows."""

    def __init__(self, db: Session):
        self.db = db
        self.trip_repo = TripRepository(db)
        self.issue_repo = TripIssueRepository(db)
        self.booking_repo = ResourceBookingRepository(db)

    def log_issue(self, trip_id: int, req: CreateTripIssueRequest, user_id: int) -> TripIssue:
        """
        Record a new incident/issue for an operational trip.
        Invariant: Does NOT complete trip and does NOT alter trip price/weight.
        """
        trip = self.trip_repo.get_by_id(trip_id)
        if not trip:
            logger.warning("Trip %s not found for logging issue", trip_id)
            raise NotFoundException(f"Không tìm thấy chuyến hàng với ID: {trip_id}")

        if not req.issue_type:
            raise BusinessRuleException("Loại sự cố không được để trống.")
        if not req.description or len(req.description.strip()) < 5:
            raise BusinessRuleException("Mô tả sự cố phải có ít nhất 5 ký tự.")

        occurred_time = req.occurred_at or datetime.now(timezone.utc)

        try:
            issue = self.issue_repo.create_issue(
                trip_id=trip.id,
                issue_type=req.issue_type,
                description=req.description.strip(),
                occurred_at=occurred_time,
                handled_by=req.handled_by.strip() if req.handled_by else None,
                estimated_resolution_time=req.estimated_resolution_time,
                reported_by_user_id=user_id,
                status=IssueStatus.OPEN.value,
            )

            # Record immutable audit event
            event = TripEvent(
                trip_id=trip.id,
                event_type=TripEventType.ISSUE_LOGGED.value,
                from_status=trip.status,
                to_status=trip.status,
                actual_time=occurred_time,
                recorded_at=datetime.now(timezone.utc),
                recorded_by_user_id=user_id,
                notes=f"Lập biên bản sự cố [{req.issue_type}]: {req.description.strip()}",
            )
            self.db.add(event)
            self.db.commit()
            self.db.refresh(issue)
            logger.info("Issue %s logged for trip %s (%s)", issue.id, trip.reference_code, req.issue_type)
            return issue
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to log issue for trip %s: %s", trip_id, e, exc_info=True)
            raise e

    def resolve_issue(self, trip_id: int, issue_id: int, req: ResolveTripIssueRequest, user_id: int) -> TripIssue:
        """
        Mark an open issue as resolved with resolution notes.
        """
        trip = self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise NotFoundException(f"Không tìm thấy chuyến hàng với ID: {trip_id}")

        issue = self.db.query(TripIssue).filter(TripIssue.id == issue_id, TripIssue.trip_id == trip_id).first()
        if not issue:
            raise NotFoundException(f"Không tìm thấy sự cố {issue_id} của chuyến hàng {trip_id}")

        if issue.status != IssueStatus.OPEN.value:
            raise BusinessRuleException("Sự cố này đã được giải quyết hoặc đã bị hủy trước đó.")

        if not req.resolution_notes or len(req.resolution_notes.strip()) < 5:
            raise BusinessRuleException("Ghi chú kết quả xử lý không được để trống và phải có ít nhất 5 ký tự.")

        try:
            resolved_issue = self.issue_repo.resolve_issue(issue.id, req.resolution_notes.strip())

            # Record audit event
            event = TripEvent(
                trip_id=trip.id,
                event_type=TripEventType.ISSUE_RESOLVED.value,
                from_status=trip.status,
                to_status=trip.status,
                actual_time=datetime.now(timezone.utc),
                recorded_at=datetime.now(timezone.utc),
                recorded_by_user_id=user_id,
                notes=f"Đã giải quyết sự cố [{issue.issue_type}]: {req.resolution_notes.strip()}",
            )
            self.db.add(event)
            self.db.commit()
            self.db.refresh(resolved_issue)
            logger.info("Issue %s resolved for trip %s", issue.id, trip.reference_code)
            return resolved_issue
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to resolve issue %s for trip %s: %s", issue_id, trip_id, e, exc_info=True)
            raise e

    def reschedule_trip(
        self, trip_id: int, new_estimated_end_time: datetime, reason: Optional[str], user_id: int
    ) -> Tuple[Trip, List[ResourceBooking]]:
        """
        Reschedule trip by extending its estimated_end_time.
        Scans for future overlapping bookings for assigned truck/driver.
        If conflicts exist: keeps current booking extended and returns conflict list for DSP alerting.
        """
        trip = self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise NotFoundException(f"Không tìm thấy chuyến hàng với ID: {trip_id}")

        if trip.estimated_start_time and new_estimated_end_time <= trip.estimated_start_time:
            raise BusinessRuleException("Thời điểm kết thúc mới phải sau thời điểm bắt đầu dự kiến của chuyến hàng.")

        old_end_time = trip.estimated_end_time or trip.estimated_start_time

        try:
            # 1. Check for overlapping future bookings for truck or driver
            conflicts = self.booking_repo.find_future_conflicts_for_resources(
                exclude_reference_code=trip.reference_code,
                truck_id=trip.assigned_truck_id,
                driver_id=trip.assigned_driver_id,
                start_time=old_end_time,
                end_time=new_estimated_end_time,
            )

            # 2. Update trip estimated_end_time
            trip.estimated_end_time = new_estimated_end_time

            # 3. Extend current trip booking end_time
            self.booking_repo.extend_booking_end_time(trip.reference_code, new_estimated_end_time)

            # 4. Record audit event
            reason_str = f" - Lý do: {reason.strip()}" if reason and reason.strip() else ""
            conflict_note = f" (Phát hiện {len(conflicts)} booking kế tiếp bị chồng lấn)" if conflicts else ""
            event = TripEvent(
                trip_id=trip.id,
                event_type=TripEventType.SCHEDULE_DELAYED.value,
                from_status=trip.status,
                to_status=trip.status,
                actual_time=datetime.now(timezone.utc),
                recorded_at=datetime.now(timezone.utc),
                recorded_by_user_id=user_id,
                notes=f"Gia hạn thời gian kết thúc đến {new_estimated_end_time.strftime('%d/%m/%Y %H:%M')}{reason_str}{conflict_note}",
            )
            self.db.add(event)
            self.db.commit()
            self.db.refresh(trip)
            logger.info(
                "Trip %s rescheduled to %s with %s conflicts",
                trip.reference_code,
                new_estimated_end_time,
                len(conflicts),
            )
            return trip, conflicts
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to reschedule trip %s: %s", trip_id, e, exc_info=True)
            raise e
