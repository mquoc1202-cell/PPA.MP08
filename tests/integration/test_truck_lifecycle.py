from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.orm import Session
from src.services.truck_service import TruckService
from src.services.driver_service import DriverService
from src.repositories.truck_repo import TruckRepository
from src.repositories.driver_repo import DriverRepository
from src.repositories.booking_repo import ResourceBookingRepository
from src.models.truck import TruckStatus
from src.models.driver import DriverStatus
from src.models.booking import ResourceBooking, ResourceType, BookingStatus
from src.schemas.truck import CreateTruckRequest
from src.schemas.driver import CreateDriverRequest
from src.core.exceptions import ScheduleConflictError

def test_truck_status_change_blocked_by_future_booking(db_session: Session):
    """
    US4 Acceptance Scenario 1:
    Given a truck has a future confirmed booking,
    When changing status to MAINTENANCE or INACTIVE,
    Then system raises ScheduleConflictError listing conflicting bookings.
    """
    truck_repo = TruckRepository(db_session)
    booking_repo = ResourceBookingRepository(db_session)
    service = TruckService(truck_repo, booking_repo)

    truck = service.create_truck(CreateTruckRequest(
        plate_number="29C-555.55",
        truck_type="Xe tải 5T",
        capacity_kg=5000
    ))

    # Future booking
    now = datetime.now(timezone.utc)
    future_start = now + timedelta(days=1)
    future_end = now + timedelta(days=2)
    booking = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code="ORDER-FUTURE-101",
        start_time=future_start,
        end_time=future_end,
        status=BookingStatus.CONFIRMED.value
    )
    booking_repo.create(booking)

    # Attempt to change to MAINTENANCE -> must raise ScheduleConflictError
    with pytest.raises(ScheduleConflictError) as exc_info:
        service.change_truck_status(truck.id, TruckStatus.MAINTENANCE)
    
    assert "lịch phân công trong tương lai" in str(exc_info.value)
    assert len(exc_info.value.conflicting_bookings) == 1
    assert exc_info.value.conflicting_bookings[0]["reference_code"] == "ORDER-FUTURE-101"

    # Status must remain ACTIVE
    persisted = truck_repo.get_by_id(truck.id)
    assert persisted.status == TruckStatus.ACTIVE.value

def test_truck_status_change_blocked_when_in_progress(db_session: Session):
    """
    US4 Acceptance Scenario 2:
    Given a truck is currently IN_PROGRESS,
    When changing status to INACTIVE,
    Then system rejects transition.
    """
    truck_repo = TruckRepository(db_session)
    booking_repo = ResourceBookingRepository(db_session)
    service = TruckService(truck_repo, booking_repo)

    truck = service.create_truck(CreateTruckRequest(
        plate_number="29C-777.77",
        truck_type="Xe tải 5T",
        capacity_kg=5000
    ))

    now = datetime.now(timezone.utc)
    booking = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code="TRIP-ACTIVE-001",
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=5),
        status=BookingStatus.IN_PROGRESS.value
    )
    booking_repo.create(booking)

    with pytest.raises(ScheduleConflictError) as exc_info:
        service.change_truck_status(truck.id, TruckStatus.INACTIVE)
    assert "IN_PROGRESS" in str(exc_info.value)

def test_driver_status_change_blocked_by_future_booking(db_session: Session):
    """
    US4 Acceptance Scenario:
    Given a driver has future assignments,
    When changing status to INACTIVE,
    Then system raises ScheduleConflictError.
    """
    driver_repo = DriverRepository(db_session)
    booking_repo = ResourceBookingRepository(db_session)
    service = DriverService(driver_repo, booking_repo)

    driver = service.create_driver(CreateDriverRequest(
        driver_code="TX777",
        full_name="Ngô Văn G",
        phone_number="0977777777"
    ))

    now = datetime.now(timezone.utc)
    booking = ResourceBooking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver.id,
        reference_code="ORDER-DRIVER-FUTURE",
        start_time=now + timedelta(days=3),
        end_time=now + timedelta(days=4),
        status=BookingStatus.CONFIRMED.value
    )
    booking_repo.create(booking)

    with pytest.raises(ScheduleConflictError) as exc_info:
        service.change_driver_status(driver.id, DriverStatus.INACTIVE)
    assert "lịch phân công trong tương lai" in str(exc_info.value)

def test_status_change_succeeds_when_no_future_bookings(db_session: Session):
    """When no future booking conflicts exist, status transitions succeed smoothly."""
    truck_repo = TruckRepository(db_session)
    booking_repo = ResourceBookingRepository(db_session)
    service = TruckService(truck_repo, booking_repo)

    truck = service.create_truck(CreateTruckRequest(
        plate_number="29C-333.33",
        truck_type="Xe tải 3T",
        capacity_kg=3000
    ))

    updated = service.change_truck_status(truck.id, TruckStatus.MAINTENANCE, reason="Thay dầu định kỳ")
    assert updated.status == TruckStatus.MAINTENANCE.value

    # Back to ACTIVE
    reactivated = service.change_truck_status(truck.id, TruckStatus.ACTIVE)
    assert reactivated.status == TruckStatus.ACTIVE.value
