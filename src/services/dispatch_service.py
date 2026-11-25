from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.core.logging import get_logger
from src.models.trip import Trip, TripStatus
from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.booking import ResourceBooking, ResourceType, BookingStatus, ServiceType
from src.repositories.trip_repo import TripRepository
from src.repositories.truck_repo import TruckRepository
from src.repositories.driver_repo import DriverRepository
from src.repositories.booking_repo import ResourceBookingRepository
from src.schemas.trip import AssignTripRequest, ReassignTripRequest
from src.core.exceptions import (
    EntityNotFoundError,
    BusinessRuleViolationError,
    ScheduleConflictError,
)

logger = get_logger("dispatch_service")


def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class DispatchService:
    """Service handling Trip Dispatching, Resource Assignment, and Concurrency Locks."""

    def __init__(self, db: Session):
        self.db = db
        self.trip_repo = TripRepository(db)
        self.truck_repo = TruckRepository(db)
        self.driver_repo = DriverRepository(db)
        self.booking_repo = ResourceBookingRepository(db)

    def assign_trip(self, trip_id: int, req: AssignTripRequest) -> Trip:
        """
        Assigns truck and driver to an UNASSIGNED trip.
        Enforces:
        - Trip is UNASSIGNED
        - Valid time interval (end_time > start_time)
        - Truck capacity >= cargo weight (BR-06)
        - Truck and driver are ACTIVE
        - Neither truck nor driver has overlapping bookings (BR-07, BR-08)
        - Atomic 2-resource booking creation
        """
        start_time = _normalize_dt(req.start_time)
        end_time = _normalize_dt(req.end_time)

        trip = self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise EntityNotFoundError(f"Chuyến hàng ID {trip_id} không tồn tại.")

        if trip.status != TripStatus.UNASSIGNED.value:
            raise BusinessRuleViolationError(
                f"Chỉ chuyến hàng chưa điều phối (UNASSIGNED) mới được gán xe và tài xế. Trạng thái hiện tại: {trip.status}"
            )

        if end_time <= start_time:
            raise BusinessRuleViolationError("Thời gian kết thúc dự kiến phải lớn hơn thời gian bắt đầu.")

        truck = self.truck_repo.get_by_id(req.truck_id)
        if not truck:
            raise EntityNotFoundError(f"Xe tải ID {req.truck_id} không tồn tại.")

        if truck.status != TruckStatus.ACTIVE.value:
            raise BusinessRuleViolationError(
                f"Xe tải {truck.plate_number} không ở trạng thái sẵn sàng (ACTIVE). Hiện tại: {truck.status}"
            )

        if truck.capacity_kg < trip.cargo_weight_kg:
            raise BusinessRuleViolationError(
                f"Khối lượng hàng hóa ({trip.cargo_weight_kg:,} kg) vượt quá tải trọng của xe ({truck.capacity_kg:,} kg)."
            )

        driver = self.driver_repo.get_by_id(req.driver_id)
        if not driver:
            raise EntityNotFoundError(f"Tài xế ID {req.driver_id} không tồn tại.")

        if driver.status != DriverStatus.ACTIVE.value:
            raise BusinessRuleViolationError(
                f"Tài xế {driver.full_name} ({driver.driver_code}) không ở trạng thái sẵn sàng (ACTIVE). Hiện tại: {driver.status}"
            )

        # Check overlapping bookings for truck
        overlapping_truck = self.booking_repo.get_overlapping_bookings(
            ResourceType.TRUCK.value, truck.id, start_time, end_time
        )
        if overlapping_truck:
            conflict_details = [
                {
                    "id": b.id,
                    "resource_type": b.resource_type,
                    "resource_id": b.resource_id,
                    "reference_code": b.reference_code,
                    "service_type": b.service_type,
                    "start_time": b.start_time.isoformat(),
                    "end_time": b.end_time.isoformat(),
                    "status": b.status,
                }
                for b in overlapping_truck
            ]
            logger.warning("Schedule conflict for truck %s during [%s, %s]", truck.plate_number, start_time, end_time)
            raise ScheduleConflictError(
                f"Xe tải {truck.plate_number} đã bị chiếm dụng trong khoảng thời gian này.",
                conflicting_bookings=conflict_details,
            )

        # Check overlapping bookings for driver
        overlapping_driver = self.booking_repo.get_overlapping_bookings(
            ResourceType.DRIVER.value, driver.id, start_time, end_time
        )
        if overlapping_driver:
            conflict_details = [
                {
                    "id": b.id,
                    "resource_type": b.resource_type,
                    "resource_id": b.resource_id,
                    "reference_code": b.reference_code,
                    "service_type": b.service_type,
                    "start_time": b.start_time.isoformat(),
                    "end_time": b.end_time.isoformat(),
                    "status": b.status,
                }
                for b in overlapping_driver
            ]
            logger.warning("Schedule conflict for driver %s during [%s, %s]", driver.driver_code, start_time, end_time)
            raise ScheduleConflictError(
                f"Tài xế {driver.full_name} ({driver.driver_code}) đã bị chiếm dụng trong khoảng thời gian này.",
                conflicting_bookings=conflict_details,
            )

        # Atomic booking execution
        try:
            truck_booking = ResourceBooking(
                resource_type=ResourceType.TRUCK.value,
                resource_id=truck.id,
                reference_code=trip.reference_code,
                service_type=ServiceType.FREIGHT.value,
                start_time=start_time,
                end_time=end_time,
                status=BookingStatus.CONFIRMED.value,
            )
            driver_booking = ResourceBooking(
                resource_type=ResourceType.DRIVER.value,
                resource_id=driver.id,
                reference_code=trip.reference_code,
                service_type=ServiceType.FREIGHT.value,
                start_time=start_time,
                end_time=end_time,
                status=BookingStatus.CONFIRMED.value,
            )

            trip.assigned_truck_id = truck.id
            trip.assigned_driver_id = driver.id
            trip.estimated_start_time = start_time
            trip.estimated_end_time = end_time
            trip.status = TripStatus.ASSIGNED.value

            self.db.add_all([truck_booking, driver_booking])
            self.db.commit()
            self.db.refresh(trip)

            logger.info("Trip %s assigned successfully to Truck %s and Driver %s", trip.reference_code, truck.plate_number, driver.driver_code)
            return trip
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to commit dispatch assignment for trip %s: %s", trip.reference_code, e, exc_info=True)
            raise e

    def reassign_trip(self, trip_id: int, req: ReassignTripRequest) -> Trip:
        """
        Changes truck and/or driver on an ASSIGNED trip before PICKED_UP.
        Releases old bookings and creates new ones atomically.
        """
        trip = self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise EntityNotFoundError(f"Chuyến hàng ID {trip_id} không tồn tại.")

        if trip.status != TripStatus.ASSIGNED.value:
            raise BusinessRuleViolationError(
                f"Chỉ chuyến hàng ở trạng thái ASSIGNED mới được phép thay đổi phân công. Khi chuyến đã nhận hàng (PICKED_UP) hoặc hoàn tất, không được phép thay đổi. Trạng thái hiện tại: {trip.status}"
            )

        start_time = _normalize_dt(req.start_time or trip.estimated_start_time)
        end_time = _normalize_dt(req.end_time or trip.estimated_end_time)

        if not start_time or not end_time or end_time <= start_time:
            raise BusinessRuleViolationError("Khoảng thời gian dự kiến không hợp lệ.")

        truck = self.truck_repo.get_by_id(req.truck_id)
        if not truck:
            raise EntityNotFoundError(f"Xe tải ID {req.truck_id} không tồn tại.")
        if truck.status != TruckStatus.ACTIVE.value:
            raise BusinessRuleViolationError(f"Xe tải {truck.plate_number} không ở trạng thái sẵn sàng.")
        if truck.capacity_kg < trip.cargo_weight_kg:
            raise BusinessRuleViolationError(
                f"Khối lượng hàng hóa ({trip.cargo_weight_kg:,} kg) vượt quá tải trọng xe ({truck.capacity_kg:,} kg)."
            )

        driver = self.driver_repo.get_by_id(req.driver_id)
        if not driver:
            raise EntityNotFoundError(f"Tài xế ID {req.driver_id} không tồn tại.")
        if driver.status != DriverStatus.ACTIVE.value:
            raise BusinessRuleViolationError(f"Tài xế {driver.full_name} không ở trạng thái sẵn sàng.")

        # Check overlapping excluding this trip's current bookings
        overlapping_truck = self.booking_repo.get_overlapping_bookings(
            ResourceType.TRUCK.value, truck.id, start_time, end_time, exclude_reference_code=trip.reference_code
        )
        if overlapping_truck:
            conflict_details = [
                {
                    "id": b.id,
                    "resource_type": b.resource_type,
                    "resource_id": b.resource_id,
                    "reference_code": b.reference_code,
                    "service_type": b.service_type,
                    "start_time": b.start_time.isoformat(),
                    "end_time": b.end_time.isoformat(),
                    "status": b.status,
                }
                for b in overlapping_truck
            ]
            logger.warning("Schedule conflict for truck %s during [%s, %s]", truck.plate_number, start_time, end_time)
            raise ScheduleConflictError(
                f"Xe tải {truck.plate_number} đã bị chiếm dụng trong khoảng thời gian này.",
                conflicting_bookings=conflict_details,
            )

        overlapping_driver = self.booking_repo.get_overlapping_bookings(
            ResourceType.DRIVER.value, driver.id, start_time, end_time, exclude_reference_code=trip.reference_code
        )
        if overlapping_driver:
            conflict_details = [
                {
                    "id": b.id,
                    "resource_type": b.resource_type,
                    "resource_id": b.resource_id,
                    "reference_code": b.reference_code,
                    "service_type": b.service_type,
                    "start_time": b.start_time.isoformat(),
                    "end_time": b.end_time.isoformat(),
                    "status": b.status,
                }
                for b in overlapping_driver
            ]
            logger.warning("Schedule conflict for driver %s during [%s, %s]", driver.driver_code, start_time, end_time)
            raise ScheduleConflictError(
                f"Tài xế {driver.full_name} ({driver.driver_code}) đã bị chiếm dụng trong khoảng thời gian này.",
                conflicting_bookings=conflict_details,
            )

        try:
            # Cancel old bookings
            old_bookings = self.db.query(ResourceBooking).filter(
                ResourceBooking.reference_code == trip.reference_code,
                ResourceBooking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.IN_PROGRESS.value]),
            ).all()
            for b in old_bookings:
                b.status = BookingStatus.CANCELLED.value

            # Create new bookings
            new_truck_booking = ResourceBooking(
                resource_type=ResourceType.TRUCK.value,
                resource_id=truck.id,
                reference_code=trip.reference_code,
                service_type=ServiceType.FREIGHT.value,
                start_time=start_time,
                end_time=end_time,
                status=BookingStatus.CONFIRMED.value,
            )
            new_driver_booking = ResourceBooking(
                resource_type=ResourceType.DRIVER.value,
                resource_id=driver.id,
                reference_code=trip.reference_code,
                service_type=ServiceType.FREIGHT.value,
                start_time=start_time,
                end_time=end_time,
                status=BookingStatus.CONFIRMED.value,
            )

            trip.assigned_truck_id = truck.id
            trip.assigned_driver_id = driver.id
            trip.estimated_start_time = start_time
            trip.estimated_end_time = end_time

            self.db.add_all([new_truck_booking, new_driver_booking])
            self.db.commit()
            self.db.refresh(trip)

            logger.info("Trip %s reassigned to Truck %s and Driver %s", trip.reference_code, truck.plate_number, driver.driver_code)
            return trip
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to reassign trip %s: %s", trip.reference_code, e, exc_info=True)
            raise e

    def unassign_trip(self, trip_id: int) -> Trip:
        """
        Revokes assignment from an ASSIGNED trip, releasing bookings and moving back to UNASSIGNED.
        """
        trip = self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise EntityNotFoundError(f"Chuyến hàng ID {trip_id} không tồn tại.")

        if trip.status != TripStatus.ASSIGNED.value:
            raise BusinessRuleViolationError(
                f"Chỉ chuyến hàng ở trạng thái ASSIGNED mới được phép hủy phân công. Trạng thái hiện tại: {trip.status}"
            )

        try:
            # Cancel active bookings
            old_bookings = self.db.query(ResourceBooking).filter(
                ResourceBooking.reference_code == trip.reference_code,
                ResourceBooking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.IN_PROGRESS.value]),
            ).all()
            for b in old_bookings:
                b.status = BookingStatus.CANCELLED.value

            trip.assigned_truck_id = None
            trip.assigned_driver_id = None
            trip.estimated_start_time = None
            trip.estimated_end_time = None
            trip.status = TripStatus.UNASSIGNED.value

            self.db.commit()
            self.db.refresh(trip)
            logger.info("Trip %s unassigned successfully and returned to UNASSIGNED", trip.reference_code)
            return trip
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to unassign trip %s: %s", trip.reference_code, e, exc_info=True)
            raise e
