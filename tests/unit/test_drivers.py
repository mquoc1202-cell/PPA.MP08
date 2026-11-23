import pytest
from sqlalchemy.orm import Session
from src.services.driver_service import DriverService
from src.repositories.driver_repo import DriverRepository
from src.repositories.booking_repo import ResourceBookingRepository
from src.schemas.driver import CreateDriverRequest, UpdateDriverRequest
from src.core.exceptions import ConflictError, BusinessRuleViolationError, EntityNotFoundError

def test_create_driver_success(db_session: Session):
    """Validates successful driver creation with unique code and phone number."""
    driver_repo = DriverRepository(db_session)
    booking_repo = ResourceBookingRepository(db_session)
    service = DriverService(driver_repo, booking_repo)

    req = CreateDriverRequest(
        driver_code="TX001",
        full_name="Nguyễn Văn A",
        phone_number="0912345678"
    )
    driver = service.create_driver(req)

    assert driver.id is not None
    assert driver.driver_code == "TX001"
    assert driver.full_name == "Nguyễn Văn A"
    assert driver.phone_number == "0912345678"
    assert driver.status == "ACTIVE"

def test_create_driver_duplicate_code(db_session: Session):
    """Validates rejection when driver code already exists."""
    driver_repo = DriverRepository(db_session)
    booking_repo = ResourceBookingRepository(db_session)
    service = DriverService(driver_repo, booking_repo)

    req1 = CreateDriverRequest(
        driver_code="TX001",
        full_name="Nguyễn Văn A",
        phone_number="0912345678"
    )
    service.create_driver(req1)

    req2 = CreateDriverRequest(
        driver_code="tx001",  # Same code after normalization
        full_name="Trần Văn B",
        phone_number="0987654321"
    )
    with pytest.raises(ConflictError) as exc_info:
        service.create_driver(req2)
    assert "đã tồn tại" in str(exc_info.value)

def test_create_driver_invalid_phone():
    """Validates phone number format validation."""
    with pytest.raises(Exception):
        CreateDriverRequest(
            driver_code="TX002",
            full_name="Lê Văn C",
            phone_number="abc"  # Invalid
        )

def test_update_driver_success(db_session: Session):
    """Validates updating driver information."""
    driver_repo = DriverRepository(db_session)
    booking_repo = ResourceBookingRepository(db_session)
    service = DriverService(driver_repo, booking_repo)

    driver = service.create_driver(CreateDriverRequest(
        driver_code="TX003",
        full_name="Hoàng Văn D",
        phone_number="0911222333"
    ))

    update_req = UpdateDriverRequest(
        full_name="Hoàng Văn D (Cập nhật)",
        phone_number="0944555666"
    )
    updated = service.update_driver(driver.id, update_req)
    assert updated.full_name == "Hoàng Văn D (Cập nhật)"
    assert updated.phone_number == "0944555666"
