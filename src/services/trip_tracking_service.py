from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from src.core.logging import get_logger
from src.core.exceptions import (
    EntityNotFoundError,
    BusinessRuleViolationError,
    ScheduleConflictError,
)
from src.models.trip import Trip, TripStatus
from src.models.trip_event import TripEvent, TripEventType
from src.models.truck import Truck
from src.models.driver import Driver
from src.models.booking import ResourceBooking, ResourceType, BookingStatus
from src.schemas.trip import RecordPickupRequest, RecordDepartureRequest
from src.repositories.trip_repo import TripRepository
from src.repositories.trip_event_repo import TripEventRepository
from src.repositories.booking_repo import ResourceBookingRepository
from src.repositories.truck_repo import TruckRepository
from src.repositories.driver_repo import DriverRepository

logger = get_logger("trip_tracking_service")


def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    """Strips timezone info to maintain naive UTC consistency in SQLite."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class TripTrackingService:
    """Business logic orchestrator for trip lifecycle milestones (TRN-03)."""

    def __init__(self, db: Session):
        self.db = db
        self.trip_repo = TripRepository(db)
        self.event_repo = TripEventRepository(db)
        self.booking_repo = ResourceBookingRepository(db)
        self.truck_repo = TruckRepository(db)
        self.driver_repo = DriverRepository(db)

    def record_pickup(
        self, trip_id: int, req: RecordPickupRequest, user_id: Optional[int] = None
    ) -> Trip:
        """
        Confirms actual cargo pickup, validates weight and BR-09 availability,
        transitions trip to PICKED_UP and bookings to IN_PROGRESS.
        """
        trip = self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise EntityNotFoundError(f"Chuyến hàng ID {trip_id} không tồn tại.")

        if trip.status != TripStatus.ASSIGNED.value:
            raise BusinessRuleViolationError(
                f"Chỉ chuyến hàng ở trạng thái ASSIGNED mới được phép xác nhận nhận hàng. Trạng thái hiện tại: {trip.status}"
            )

        if not trip.assigned_truck_id or not trip.assigned_driver_id:
            raise BusinessRuleViolationError("Chuyến hàng chưa được phân công xe hoặc tài xế hợp lệ.")

        truck = self.truck_repo.get_by_id(trip.assigned_truck_id)
        if not truck:
            raise EntityNotFoundError(f"Xe tải phân công ID {trip.assigned_truck_id} không tồn tại.")

        # BR-06: Overweight validation
        if req.actual_cargo_weight_kg > truck.capacity_kg:
            logger.warning(
                "Pickup rejected for trip %s: Actual weight %s kg exceeds truck capacity %s kg",
                trip.reference_code,
                req.actual_cargo_weight_kg,
                truck.capacity_kg,
            )
            raise BusinessRuleViolationError(
                f"Khối lượng hàng thực tế ({req.actual_cargo_weight_kg:,} kg) vượt quá tải trọng của xe {truck.plate_number} ({truck.capacity_kg:,} kg). Hệ thống không cho phép nhận hàng quá tải."
            )

        # BR-09: Check if truck or driver is busy with another in-progress trip
        truck_busy = self.booking_repo.has_in_progress_booking(
            ResourceType.TRUCK.value, truck.id, exclude_reference_code=trip.reference_code
        )
        if truck_busy:
            raise ScheduleConflictError(
                f"Xe tải {truck.plate_number} hiện đang thực hiện một chuyến hàng khác chưa hoàn tất (BR-09)."
            )

        driver_busy = self.booking_repo.has_in_progress_booking(
            ResourceType.DRIVER.value, trip.assigned_driver_id, exclude_reference_code=trip.reference_code
        )
        if driver_busy:
            raise ScheduleConflictError(
                "Tài xế hiện đang thực hiện một chuyến hàng khác chưa hoàn tất (BR-09)."
            )

        actual_pickup_time = _normalize_dt(req.actual_pickup_time)
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        try:
            trip.status = TripStatus.PICKED_UP.value
            trip.actual_cargo_weight_kg = req.actual_cargo_weight_kg
            trip.handover_person = req.handover_person
            trip.cargo_condition = req.cargo_condition
            trip.discrepancy_notes = req.discrepancy_notes
            trip.actual_pickup_time = actual_pickup_time
            trip.pickup_recorded_at = now_utc

            # Sync bookings to IN_PROGRESS
            self.booking_repo.transition_bookings_status(
                reference_code=trip.reference_code,
                from_status=BookingStatus.CONFIRMED.value,
                to_status=BookingStatus.IN_PROGRESS.value,
            )

            # Log audit timeline event
            self.event_repo.log_event(
                trip_id=trip.id,
                event_type=TripEventType.PICKUP_CONFIRMED.value,
                from_status=TripStatus.ASSIGNED.value,
                to_status=TripStatus.PICKED_UP.value,
                actual_time=actual_pickup_time,
                recorded_by_user_id=user_id,
                notes=req.discrepancy_notes or f"Khối lượng thực tế: {req.actual_cargo_weight_kg:,} kg",
            )

            self.db.commit()
            self.db.refresh(trip)
            logger.info("Trip %s successfully confirmed pickup (PICKED_UP)", trip.reference_code)
            return trip
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to record pickup for trip %s: %s", trip.reference_code, e, exc_info=True)
            raise e

    def record_departure(
        self, trip_id: int, req: RecordDepartureRequest, user_id: Optional[int] = None
    ) -> Trip:
        """
        Confirms actual departure from pickup location, transitioning trip to IN_TRANSIT.
        """
        trip = self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise EntityNotFoundError(f"Chuyến hàng ID {trip_id} không tồn tại.")

        if trip.status != TripStatus.PICKED_UP.value:
            raise BusinessRuleViolationError(
                f"Chỉ chuyến hàng ở trạng thái PICKED_UP mới được phép xác nhận khởi hành sang IN_TRANSIT. Trạng thái hiện tại: {trip.status}"
            )

        actual_depart_time = _normalize_dt(req.actual_depart_time)
        if trip.actual_pickup_time and actual_depart_time < trip.actual_pickup_time:
            raise BusinessRuleViolationError(
                f"Thời điểm khởi hành ({actual_depart_time}) không được diễn ra trước thời điểm nhận hàng ({trip.actual_pickup_time})."
            )

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        try:
            trip.status = TripStatus.IN_TRANSIT.value
            trip.actual_depart_time = actual_depart_time
            trip.depart_recorded_at = now_utc

            self.event_repo.log_event(
                trip_id=trip.id,
                event_type=TripEventType.DEPARTURE_CONFIRMED.value,
                from_status=TripStatus.PICKED_UP.value,
                to_status=TripStatus.IN_TRANSIT.value,
                actual_time=actual_depart_time,
                recorded_by_user_id=user_id,
                notes=req.notes or "Xe xuất phát di chuyển theo lộ trình",
            )

            self.db.commit()
            self.db.refresh(trip)
            logger.info("Trip %s successfully transitioned to IN_TRANSIT", trip.reference_code)
            return trip
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to record departure for trip %s: %s", trip.reference_code, e, exc_info=True)
            raise e
