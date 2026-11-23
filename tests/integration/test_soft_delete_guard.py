from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.orm import Session
from src.services.truck_service import TruckService
from src.services.driver_service import DriverService
from src.repositories.truck_repo import TruckRepository
from src.repositories.driver_repo import DriverRepository
from src.repositories.booking_repo import ResourceBookingRepository
from src.models.booking import ResourceBooking, ResourceType, BookingStatus
from src.schemas.truck import CreateTruckRequest
from src.schemas.driver import CreateDriverRequest
from src.core.exceptions import BusinessRuleViolationError

def test_truck_soft_delete_guard(db_session: Session):
    """
    US3 Acceptance Scenario:
    Given a truck has a booking record in ResourceBooking,
    When user attempts to delete the truck,
    Then system rejects hard deletion with BusinessRuleViolationError.
    """
    truck_repo = TruckRepository(db_session)
    booking_repo = ResourceBookingRepository(db_session)
    service = TruckService(truck_repo, booking_repo)

    # Create truck
    truck = service.create_truck(CreateTruckRequest(
        plate_number="29C-888.88",
        truck_type="Xe tải 10T",
        capacity_kg=10000
    ))

    # Add historical booking
    now = datetime.now(timezone.utc)
    booking = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code="ORDER-2026-001",
        start_time=now - timedelta(days=2),
        end_time=now - timedelta(days=1),
        status=BookingStatus.COMPLETED.value
    )
    booking_repo.create(booking)

    # Attempt hard delete -> must fail
    with pytest.raises(BusinessRuleViolationError) as exc_info:
        service.delete_truck(truck.id)
    assert "Không thể xóa xe đã có lịch sử hoạt động" in str(exc_info.value)

    # Verify truck still exists in database
    persisted = truck_repo.get_by_id(truck.id)
    assert persisted is not None

def test_driver_soft_delete_guard(db_session: Session):
    """
    US3 Acceptance Scenario:
    Given a driver has a booking record,
    When user attempts to delete the driver,
    Then system rejects hard deletion with BusinessRuleViolationError.
    """
    driver_repo = DriverRepository(db_session)
    booking_repo = ResourceBookingRepository(db_session)
    service = DriverService(driver_repo, booking_repo)

    # Create driver
    driver = service.create_driver(CreateDriverRequest(
        driver_code="TX999",
        full_name="Vũ Văn E",
        phone_number="0933333333"
    ))

    # Add booking history
    now = datetime.now(timezone.utc)
    booking = ResourceBooking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver.id,
        reference_code="TRIP-999",
        start_time=now - timedelta(hours=10),
        end_time=now - timedelta(hours=2),
        status=BookingStatus.COMPLETED.value
    )
    booking_repo.create(booking)

    # Attempt hard delete -> must fail
    with pytest.raises(BusinessRuleViolationError) as exc_info:
        service.delete_driver(driver.id)
    assert "Không thể xóa tài xế đã có lịch sử hoạt động" in str(exc_info.value)

    # Verify driver record is preserved
    persisted = driver_repo.get_by_id(driver.id)
    assert persisted is not None

def test_truck_deletion_allowed_when_no_history(db_session: Session):
    """If a resource never participated in any transaction, clean deletion is permitted."""
    truck_repo = TruckRepository(db_session)
    booking_repo = ResourceBookingRepository(db_session)
    service = TruckService(truck_repo, booking_repo)

    truck = service.create_truck(CreateTruckRequest(
        plate_number="30E-123.45",
        truck_type="Xe tải nhẹ 1T",
        capacity_kg=1000
    ))

    service.delete_truck(truck.id)
    assert truck_repo.get_by_id(truck.id) is None
