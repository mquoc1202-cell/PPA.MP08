import os
import uuid
import re
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from src.models.trip import Trip, TripStatus
from src.models.trip_event import TripEvent, TripEventType
from src.models.trip_evidence import TripEvidence
from src.models.trip_issue import TripIssue, IssueStatus
from src.models.booking import ResourceBooking, BookingStatus
from src.repositories.trip_repo import TripRepository
from src.repositories.trip_event_repo import TripEventRepository
from src.repositories.trip_evidence_repo import TripEvidenceRepository
from src.repositories.trip_issue_repo import TripIssueRepository
from src.repositories.booking_repo import ResourceBookingRepository
from src.schemas.trip import RecordDeliveryRequest, CompleteTripRequest
from src.core.exceptions import BusinessRuleViolationError, EntityNotFoundError
from src.core.logging import get_logger

logger = get_logger("delivery_service")

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
UPLOAD_DIR = os.path.join("src", "static", "uploads", "evidence")


@dataclass
class UploadedEvidenceFile:
    filename: str
    content: bytes
    content_type: str
    evidence_type: str = "POD"
    notes: Optional[str] = None


def _normalize_dt(dt: datetime) -> datetime:
    """Normalize datetime to naive UTC datetime for consistent comparisons in SQLite."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _sanitize_filename(name: str) -> str:
    """Sanitize filename to prevent directory traversal and remove unsafe chars."""
    basename = os.path.basename(name)
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "_", basename)
    return sanitized or "file"


class DeliveryService:
    """
    Business service orchestrating Cargo Delivery confirmation,
    Proof of Delivery (POD) document processing, incident reporting,
    and trip completion with resource release (TRN-04).
    """

    def __init__(self, db: Session):
        self.db = db
        self.trip_repo = TripRepository(db)
        self.event_repo = TripEventRepository(db)
        self.evidence_repo = TripEvidenceRepository(db)
        self.issue_repo = TripIssueRepository(db)
        self.booking_repo = ResourceBookingRepository(db)

    def _save_file_to_disk(self, file: UploadedEvidenceFile) -> str:
        """Saves file bytes to disk with unique UUID prefix and returns relative file_path."""
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        unique_prefix = uuid.uuid4().hex[:12]
        safe_name = _sanitize_filename(file.filename)
        stored_filename = f"{unique_prefix}_{safe_name}"
        full_path = os.path.join(UPLOAD_DIR, stored_filename)

        with open(full_path, "wb") as f:
            f.write(file.content)

        # Store relative web path
        return f"uploads/evidence/{stored_filename}"

    def record_delivery(
        self,
        trip_id: int,
        req: RecordDeliveryRequest,
        files: List[UploadedEvidenceFile],
        user_id: Optional[int] = None,
    ) -> Trip:
        """
        Record cargo delivery result for an IN_TRANSIT trip (TRN-04).
        - If result == 'SUCCESS': requires recipient_name, valid timestamp, and >= 1 POD file.
          Transitions trip to DELIVERED.
        - If result == 'FAILED': retains IN_TRANSIT, logs TripIssue, logs TripEvent.
        """
        trip = self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise EntityNotFoundError(f"Chuyến hàng với ID {trip_id} không tồn tại.")

        if trip.status != TripStatus.IN_TRANSIT.value:
            raise BusinessRuleViolationError(
                f"Chỉ có thể ghi nhận giao hàng cho chuyến đang ở trạng thái IN_TRANSIT (hiện tại: {trip.status})."
            )

        norm_delivery_time = _normalize_dt(req.actual_delivery_time)
        norm_pickup_time = _normalize_dt(trip.actual_pickup_time)

        if norm_pickup_time and norm_delivery_time < norm_pickup_time:
            raise BusinessRuleViolationError(
                f"Thời điểm giao hàng thực tế ({norm_delivery_time.strftime('%d/%m/%Y %H:%M')}) "
                f"không được trước thời điểm nhận hàng ({norm_pickup_time.strftime('%d/%m/%Y %H:%M')})."
            )

        is_success = (req.result.upper() == "SUCCESS")

        if is_success:
            if not files or len(files) == 0:
                raise BusinessRuleViolationError(
                    "Bắt buộc phải tải lên ít nhất một tệp chứng từ giao hàng (POD) khi xác nhận giao thành công."
                )

            # Validate each file
            for f in files:
                if len(f.content) > MAX_FILE_SIZE:
                    raise BusinessRuleViolationError(
                        f"Tệp '{f.filename}' vượt quá dung lượng tối đa cho phép (10 MB)."
                    )
                if f.content_type.lower() not in ALLOWED_MIME_TYPES:
                    raise BusinessRuleViolationError(
                        f"Định dạng tệp '{f.filename}' ({f.content_type}) không được hỗ trợ. "
                        f"Hệ thống chỉ chấp nhận PDF, JPG, JPEG, PNG."
                    )

            # Save files and create TripEvidence records
            for f in files:
                saved_path = self._save_file_to_disk(f)
                self.evidence_repo.add_evidence(
                    trip_id=trip.id,
                    file_path=saved_path,
                    file_name=f.filename,
                    file_size_bytes=len(f.content),
                    mime_type=f.content_type,
                    evidence_type=f.evidence_type or "POD",
                    notes=f.notes,
                    uploaded_by_user_id=user_id,
                )

            # Update Trip to DELIVERED
            now_utc = datetime.now(timezone.utc)
            trip.status = TripStatus.DELIVERED.value
            trip.actual_delivery_time = norm_delivery_time
            trip.recipient_name = req.recipient_name
            trip.delivery_notes = req.delivery_notes
            trip.delivery_recorded_at = now_utc

            # Log TripEvent
            self.event_repo.log_event(
                trip_id=trip.id,
                event_type=TripEventType.DELIVERY_CONFIRMED.value,
                from_status=TripStatus.IN_TRANSIT.value,
                to_status=TripStatus.DELIVERED.value,
                actual_time=norm_delivery_time,
                recorded_by_user_id=user_id,
                notes=f"Người nhận: {req.recipient_name}. Ghi chú: {req.delivery_notes or 'Giao thành công'}",
            )
            self.db.commit()
            self.db.refresh(trip)
            logger.info("Trip %s transitioned to DELIVERED by user %s.", trip.reference_code, user_id)
            return trip

        else:
            # Result == 'FAILED'
            # Save any attached incident photos/files
            if files:
                for f in files:
                    if len(f.content) <= MAX_FILE_SIZE and f.content_type.lower() in ALLOWED_MIME_TYPES:
                        saved_path = self._save_file_to_disk(f)
                        self.evidence_repo.add_evidence(
                            trip_id=trip.id,
                            file_path=saved_path,
                            file_name=f.filename,
                            file_size_bytes=len(f.content),
                            mime_type=f.content_type,
                            evidence_type="INCIDENT_PHOTO",
                            notes="Ảnh đính kèm sự cố giao hàng thất bại",
                            uploaded_by_user_id=user_id,
                        )

            # Create TripIssue
            issue_desc = req.delivery_notes or "Giao hàng thất bại tại điểm giao."
            self.issue_repo.create_issue(
                trip_id=trip.id,
                issue_type="DELIVERY_FAILED",
                description=issue_desc,
                reported_by_user_id=user_id,
                status=IssueStatus.OPEN.value,
            )

            # Log TripEvent (remains IN_TRANSIT)
            self.event_repo.log_event(
                trip_id=trip.id,
                event_type=TripEventType.DELIVERY_FAILED.value,
                from_status=TripStatus.IN_TRANSIT.value,
                to_status=TripStatus.IN_TRANSIT.value,
                actual_time=norm_delivery_time,
                recorded_by_user_id=user_id,
                notes=f"Sự cố giao hàng: {issue_desc}",
            )
            self.db.commit()
            self.db.refresh(trip)
            logger.warning("Trip %s reported DELIVERY_FAILED by user %s. Retained IN_TRANSIT.", trip.reference_code, user_id)
            return trip

    def complete_trip(
        self,
        trip_id: int,
        req: CompleteTripRequest,
        user_id: Optional[int] = None,
    ) -> Trip:
        """
        Close a DELIVERED trip, transition to COMPLETED, and release truck & driver bookings (TRN-04).
        """
        trip = self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise EntityNotFoundError(f"Chuyến hàng với ID {trip_id} không tồn tại.")

        if trip.status != TripStatus.DELIVERED.value:
            raise BusinessRuleViolationError(
                f"Chỉ có thể hoàn tất chuyến hàng khi đang ở trạng thái DELIVERED (hiện tại: {trip.status})."
            )

        # Check evidence count
        evidence_count = self.evidence_repo.count_by_trip(trip.id)
        if evidence_count == 0:
            raise BusinessRuleViolationError(
                "Không thể hoàn tất chuyến hàng khi chưa có tệp chứng từ bàn giao (POD)."
            )

        norm_completed_time = _normalize_dt(req.actual_completed_time)
        norm_delivery_time = _normalize_dt(trip.actual_delivery_time)

        if norm_delivery_time and norm_completed_time < norm_delivery_time:
            raise BusinessRuleViolationError(
                f"Thời điểm hoàn tất ({norm_completed_time.strftime('%d/%m/%Y %H:%M')}) "
                f"không được trước thời điểm giao hàng ({norm_delivery_time.strftime('%d/%m/%Y %H:%M')})."
            )

        now_naive = datetime.now()
        # Allow small buffer of 5 minutes for slight clock discrepancy
        if norm_completed_time > now_naive + timedelta(minutes=5):
            raise BusinessRuleViolationError(
                "Thời điểm hoàn tất không được nằm ở tương lai so với thời điểm hiện tại."
            )

        # Update trip to COMPLETED
        now_utc = datetime.now(timezone.utc)
        trip.status = TripStatus.COMPLETED.value
        trip.actual_completed_time = norm_completed_time
        trip.completed_recorded_at = now_utc

        # Transition ResourceBookings to COMPLETED and update end_time
        released_count = self.booking_repo.complete_bookings_for_trip(
            reference_code=trip.reference_code,
            completed_time=norm_completed_time,
        )

        # Log TripEvent
        self.event_repo.log_event(
            trip_id=trip.id,
            event_type=TripEventType.TRIP_COMPLETED.value,
            from_status=TripStatus.DELIVERED.value,
            to_status=TripStatus.COMPLETED.value,
            actual_time=norm_completed_time,
            recorded_by_user_id=user_id,
            notes=req.notes or f"Hoàn tất chuyến hàng. Giải phóng {released_count} lịch chiếm dụng nguồn lực.",
        )

        self.db.commit()
        self.db.refresh(trip)
        logger.info(
            "Trip %s successfully COMPLETED by user %s. Released %s resource bookings.",
            trip.reference_code,
            user_id,
            released_count,
        )
        return trip
