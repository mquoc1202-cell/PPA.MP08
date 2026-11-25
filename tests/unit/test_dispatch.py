import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.trip import Trip, TripStatus
from src.models.booking import ResourceBooking, ResourceType, BookingStatus
from src.services.dispatch_service import DispatchService
from src.schemas.trip import AssignTripRequest
from src.core.exceptions import (
    BusinessRuleViolationError,
    ScheduleConflictError,
    EntityNotFoundError,
)


@pytest.fixture
def dispatch_fixture(db_session: Session):
    """Provides sample truck, driver, and trip for dispatching tests."""
    truck = Truck(
        plate_number="29C-888.88",
        normalized_plate="29C88888",
        truck_type="Xe tải 5T",
        capacity_kg=5000,
        status=TruckStatus.ACTIVE.value,
    )
    driver = Driver(
        driver_code="TX888",
        full_name="Nguyễn Văn Test",
        phone_number="0988888888",
        status=DriverStatus.ACTIVE.value,
    )
    trip = Trip(
        reference_code="TRIP-TEST-001",
        sender_name="Người gửi Test",
        sender_phone="0911223344",
        pickup_address="Hà Nội",
        delivery_address="Hải Phòng",
        cargo_weight_kg=4000,
        cargo_type="Hàng gia dụng",
        status=TripStatus.UNASSIGNED.value,
    )
    db_session.add_all([truck, driver, trip])
    db_session.flush()
    return {"truck": truck, "driver": driver, "trip": trip}


def test_assign_trip_success(db_session: Session, dispatch_fixture):
    """US1 Scenario 1: Valid assignment moves trip to ASSIGNED and creates 2 confirmed bookings."""
    service = DispatchService(db_session)
    truck = dispatch_fixture["truck"]
    driver = dispatch_fixture["driver"]
    trip = dispatch_fixture["trip"]

    now = datetime.now(timezone.utc)
    start_time = now + timedelta(days=1)
    end_time = now + timedelta(days=2)

    updated_trip = service.assign_trip(
        trip_id=trip.id,
        req=AssignTripRequest(
            truck_id=truck.id,
            driver_id=driver.id,
            start_time=start_time,
            end_time=end_time,
        ),
    )

    assert updated_trip.status == TripStatus.ASSIGNED.value
    assert updated_trip.assigned_truck_id == truck.id
    assert updated_trip.assigned_driver_id == driver.id
    assert updated_trip.estimated_start_time == start_time.replace(tzinfo=None)
    assert updated_trip.estimated_end_time == end_time.replace(tzinfo=None)

    # Verify 2 bookings were created in database
    bookings = db_session.query(ResourceBooking).filter(
        ResourceBooking.reference_code == trip.reference_code,
        ResourceBooking.status == BookingStatus.CONFIRMED.value,
    ).all()
    assert len(bookings) == 2
    types = {b.resource_type for b in bookings}
    assert types == {ResourceType.TRUCK.value, ResourceType.DRIVER.value}


def test_assign_trip_overweight_rejection(db_session: Session, dispatch_fixture):
    """US1 Scenario 2: Rejects assignment when cargo weight exceeds truck capacity (BR-06)."""
    service = DispatchService(db_session)
    truck = dispatch_fixture["truck"]
    driver = dispatch_fixture["driver"]
    trip = dispatch_fixture["trip"]

    # Increase cargo weight above truck capacity (5000 kg)
    trip.cargo_weight_kg = 6000
    db_session.flush()

    now = datetime.now(timezone.utc)
    req = AssignTripRequest(
        truck_id=truck.id,
        driver_id=driver.id,
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=2),
    )

    with pytest.raises(BusinessRuleViolationError) as exc:
        service.assign_trip(trip.id, req)
    assert "vượt quá tải trọng" in str(exc.value)

    # Verify atomic rejection: trip remains UNASSIGNED and 0 bookings created
    assert trip.status == TripStatus.UNASSIGNED.value
    bookings = db_session.query(ResourceBooking).filter(
        ResourceBooking.reference_code == trip.reference_code
    ).count()
    assert bookings == 0


def test_assign_trip_inactive_resource_rejection(db_session: Session, dispatch_fixture):
    """US1 Scenario 4: Rejects assignment when truck or driver is not ACTIVE."""
    service = DispatchService(db_session)
    truck = dispatch_fixture["truck"]
    driver = dispatch_fixture["driver"]
    trip = dispatch_fixture["trip"]

    # Set truck to MAINTENANCE
    truck.status = TruckStatus.MAINTENANCE.value
    db_session.flush()

    now = datetime.now(timezone.utc)
    req = AssignTripRequest(
        truck_id=truck.id,
        driver_id=driver.id,
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=2),
    )

    with pytest.raises(BusinessRuleViolationError) as exc:
        service.assign_trip(trip.id, req)
    assert "không ở trạng thái sẵn sàng" in str(exc.value)

    # Revert truck and set driver to INACTIVE
    truck.status = TruckStatus.ACTIVE.value
    driver.status = DriverStatus.INACTIVE.value
    db_session.flush()

    with pytest.raises(BusinessRuleViolationError) as exc2:
        service.assign_trip(trip.id, req)
    assert "không ở trạng thái sẵn sàng" in str(exc2.value)


def test_assign_trip_schedule_conflict_truck(db_session: Session, dispatch_fixture):
    """US1 Scenario 3: Rejects assignment when truck has overlapping booking (BR-07)."""
    service = DispatchService(db_session)
    truck = dispatch_fixture["truck"]
    driver = dispatch_fixture["driver"]
    trip = dispatch_fixture["trip"]

    now = datetime.now(timezone.utc)
    start_time = now + timedelta(days=1)
    end_time = now + timedelta(days=3)

    # Create existing overlapping booking for this truck
    existing_booking = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code="ORDER-EXISTING-01",
        start_time=now + timedelta(days=2),
        end_time=now + timedelta(days=4),
        status=BookingStatus.CONFIRMED.value,
    )
    db_session.add(existing_booking)
    db_session.flush()

    req = AssignTripRequest(
        truck_id=truck.id,
        driver_id=driver.id,
        start_time=start_time,
        end_time=end_time,
    )

    with pytest.raises(ScheduleConflictError) as exc:
        service.assign_trip(trip.id, req)
    assert "Xe" in str(exc.value)
    assert len(exc.value.conflicting_bookings) >= 1

    # Atomicity: trip remains UNASSIGNED and driver was NOT booked
    assert trip.status == TripStatus.UNASSIGNED.value
    driver_bookings = db_session.query(ResourceBooking).filter(
        ResourceBooking.reference_code == trip.reference_code
    ).count()
    assert driver_bookings == 0


def test_assign_trip_schedule_conflict_driver(db_session: Session, dispatch_fixture):
    """US1 Scenario 3: Rejects assignment when driver has overlapping booking (BR-08)."""
    service = DispatchService(db_session)
    truck = dispatch_fixture["truck"]
    driver = dispatch_fixture["driver"]
    trip = dispatch_fixture["trip"]

    now = datetime.now(timezone.utc)
    start_time = now + timedelta(days=1)
    end_time = now + timedelta(days=3)

    # Create existing overlapping booking for this driver
    existing_booking = ResourceBooking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver.id,
        reference_code="ORDER-EXISTING-02",
        start_time=now + timedelta(days=2),
        end_time=now + timedelta(days=4),
        status=BookingStatus.CONFIRMED.value,
    )
    db_session.add(existing_booking)
    db_session.flush()

    req = AssignTripRequest(
        truck_id=truck.id,
        driver_id=driver.id,
        start_time=start_time,
        end_time=end_time,
    )

    with pytest.raises(ScheduleConflictError) as exc:
        service.assign_trip(trip.id, req)
    assert "Tài xế" in str(exc.value)

    # Atomicity: trip remains UNASSIGNED and truck was NOT booked
    assert trip.status == TripStatus.UNASSIGNED.value
    truck_bookings = db_session.query(ResourceBooking).filter(
        ResourceBooking.reference_code == trip.reference_code
    ).count()
    assert truck_bookings == 0
