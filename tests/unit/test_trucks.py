import pytest
from sqlalchemy.orm import Session
from src.services.truck_service import TruckService
from src.repositories.truck_repo import TruckRepository
from src.repositories.booking_repo import ResourceBookingRepository
from src.schemas.truck import CreateTruckRequest, UpdateTruckRequest
from src.core.exceptions import ConflictError, BusinessRuleViolationError, EntityNotFoundError

def test_normalize_plate_number():
    """Validates plate normalization: removes spaces, dots, dashes and converts to uppercase."""
    assert TruckService.normalize_plate_number("29C-123.45") == "29C12345"
    assert TruckService.normalize_plate_number("29c 12345") == "29C12345"
    assert TruckService.normalize_plate_number(" 51D - 999.88 ") == "51D99988"
    assert TruckService.normalize_plate_number("30A.111-22") == "30A11122"

def test_create_truck_success(db_session: Session):
    """Validates successful truck creation with normalized plate and positive capacity."""
    truck_repo = TruckRepository(db_session)
    booking_repo = ResourceBookingRepository(db_session)
    service = TruckService(truck_repo, booking_repo)

    req = CreateTruckRequest(
        plate_number="29C-123.45",
        truck_type="Xe thùng kín 5T",
        capacity_kg=5000,
        description="Xe mới nhận"
    )
    truck = service.create_truck(req)

    assert truck.id is not None
    assert truck.plate_number == "29C-123.45"
    assert truck.normalized_plate == "29C12345"
    assert truck.capacity_kg == 5000
    assert truck.status == "ACTIVE"

def test_create_truck_duplicate_normalized_plate(db_session: Session):
    """Validates duplicate rejection when normalized plate collides."""
    truck_repo = TruckRepository(db_session)
    booking_repo = ResourceBookingRepository(db_session)
    service = TruckService(truck_repo, booking_repo)

    req1 = CreateTruckRequest(
        plate_number="29C-123.45",
        truck_type="Xe tải 5T",
        capacity_kg=5000
    )
    service.create_truck(req1)

    req2 = CreateTruckRequest(
        plate_number="29c 123.45",  # Same after normalization: 29C12345
        truck_type="Xe tải 3T",
        capacity_kg=3000
    )
    with pytest.raises(ConflictError) as exc_info:
        service.create_truck(req2)
    assert "đã tồn tại" in str(exc_info.value)

def test_create_truck_negative_or_zero_capacity():
    """Validates that capacity <= 0 is rejected at Schema validation level."""
    with pytest.raises(Exception):
        CreateTruckRequest(
            plate_number="29C-999.99",
            truck_type="Xe tải",
            capacity_kg=0  # Invalid
        )

    with pytest.raises(Exception):
        CreateTruckRequest(
            plate_number="29C-999.99",
            truck_type="Xe tải",
            capacity_kg=-500  # Invalid
        )

def test_update_truck_success(db_session: Session):
    """Validates updating truck details and capacity."""
    truck_repo = TruckRepository(db_session)
    booking_repo = ResourceBookingRepository(db_session)
    service = TruckService(truck_repo, booking_repo)

    truck = service.create_truck(CreateTruckRequest(
        plate_number="29C-111.11",
        truck_type="Xe tải 5T",
        capacity_kg=5000
    ))

    update_req = UpdateTruckRequest(
        plate_number="29C-111.11",
        truck_type="Xe thùng bạt 5T",
        capacity_kg=5500,
        description="Đã nâng cấp thùng"
    )
    updated = service.update_truck(truck.id, update_req)
    assert updated.truck_type == "Xe thùng bạt 5T"
    assert updated.capacity_kg == 5500
