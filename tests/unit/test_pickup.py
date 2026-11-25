import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.trip import Trip, TripStatus
from src.models.trip_event import TripEvent, TripEventType
from src.models.booking import ResourceBooking, ResourceType, BookingStatus, ServiceType
from src.schemas.trip import RecordPickupRequest, RecordDepartureRequest
from src.services.trip_tracking_service import TripTrackingService
from src.core.exceptions import BusinessRuleViolationError, EntityNotFoundError


def _setup_pickup_fixtures(db: Session):
    truck = Truck(
        plate_number="51C-PKUP.01",
        normalized_plate="51CPKUP01",
        truck_type="Tải nhẹ 5T",
        capacity_kg=5000,
        status=TruckStatus.ACTIVE.value,
    )
    driver = Driver(
        driver_code="DRV_PK01",
        full_name="Driver Pickup One",
        phone_number="0911555555",
        status=DriverStatus.ACTIVE.value,
    )
    db.add_all([truck, driver])
    db.commit()
    db.refresh(truck)
    db.refresh(driver)

    now = datetime.now()
    trip = Trip(
        reference_code="TRIP-TEST-PKUP-01",
        sender_name="Công ty May Mặc Test",
        sender_phone="0901234567",
        pickup_address="Kho A, Tân Bình",
        delivery_address="Kho B, Sóng Thần",
        cargo_type="Vải sợi",
        cargo_weight_kg=4000,
        status=TripStatus.ASSIGNED.value,
        assigned_truck_id=truck.id,
        assigned_driver_id=driver.id,
        estimated_start_time=now,
        estimated_end_time=now + timedelta(hours=6),
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)

    # Add confirmed bookings for truck and driver
    b_truck = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code=trip.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=now,
        end_time=now + timedelta(hours=6),
        status=BookingStatus.CONFIRMED.value,
    )
    b_driver = ResourceBooking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver.id,
        reference_code=trip.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=now,
        end_time=now + timedelta(hours=6),
        status=BookingStatus.CONFIRMED.value,
    )
    db.add_all([b_truck, b_driver])
    db.commit()
    return truck, driver, trip


def test_record_pickup_success(db_session: Session):
    truck, driver, trip = _setup_pickup_fixtures(db_session)
    service = TripTrackingService(db_session)

    pickup_time = datetime(2026, 12, 1, 9, 30)
    req = RecordPickupRequest(
        actual_pickup_time=pickup_time,
        handover_person="Nguyễn Văn Kho Trưởng",
        actual_cargo_weight_kg=4200,
        cargo_condition="Bao bì nguyên vẹn",
        discrepancy_notes="Tăng 200kg nhưng vẫn trong tải trọng",
    )

    updated_trip = service.record_pickup(trip.id, req, user_id=1)

    # 1. Check Trip status and fields
    assert updated_trip.status == TripStatus.PICKED_UP.value
    assert updated_trip.actual_cargo_weight_kg == 4200
    assert updated_trip.handover_person == "Nguyễn Văn Kho Trưởng"
    assert updated_trip.cargo_condition == "Bao bì nguyên vẹn"
    assert updated_trip.discrepancy_notes == "Tăng 200kg nhưng vẫn trong tải trọng"
    assert updated_trip.actual_pickup_time == pickup_time
    assert updated_trip.pickup_recorded_at is not None

    # 2. Check bookings updated to IN_PROGRESS
    bookings = db_session.query(ResourceBooking).filter(
        ResourceBooking.reference_code == trip.reference_code
    ).all()
    assert len(bookings) == 2
    assert all(b.status == BookingStatus.IN_PROGRESS.value for b in bookings)

    # 3. Check TripEvent created
    events = db_session.query(TripEvent).filter(TripEvent.trip_id == trip.id).all()
    assert len(events) == 1
    assert events[0].event_type == TripEventType.PICKUP_CONFIRMED.value
    assert events[0].from_status == TripStatus.ASSIGNED.value
    assert events[0].to_status == TripStatus.PICKED_UP.value
    assert events[0].actual_time == pickup_time


def test_record_pickup_invalid_state_rejection(db_session: Session):
    truck, driver, trip = _setup_pickup_fixtures(db_session)
    service = TripTrackingService(db_session)

    # Set status to UNASSIGNED
    trip.status = TripStatus.UNASSIGNED.value
    db_session.commit()

    req = RecordPickupRequest(
        actual_pickup_time=datetime(2026, 12, 1, 9, 30),
        handover_person="Nguyễn Văn Kho",
        actual_cargo_weight_kg=4000,
    )

    with pytest.raises(BusinessRuleViolationError) as exc_info:
        service.record_pickup(trip.id, req)
    assert "ASSIGNED" in str(exc_info.value)


def test_record_pickup_overweight_rejection(db_session: Session):
    truck, driver, trip = _setup_pickup_fixtures(db_session)
    service = TripTrackingService(db_session)

    # truck capacity is 5000 kg, actual weight is 5200 kg -> Must be rejected
    req = RecordPickupRequest(
        actual_pickup_time=datetime(2026, 12, 1, 9, 30),
        handover_person="Nguyễn Văn Kho",
        actual_cargo_weight_kg=5200,
    )

    with pytest.raises(BusinessRuleViolationError) as exc_info:
        service.record_pickup(trip.id, req)
    assert "vượt quá tải trọng" in str(exc_info.value)

    # Verify trip remains ASSIGNED and bookings remain CONFIRMED
    db_session.refresh(trip)
    assert trip.status == TripStatus.ASSIGNED.value
    assert trip.actual_cargo_weight_kg is None

    bookings = db_session.query(ResourceBooking).filter(
        ResourceBooking.reference_code == trip.reference_code
    ).all()
    assert all(b.status == BookingStatus.CONFIRMED.value for b in bookings)


def test_record_pickup_exact_capacity_accepted(db_session: Session):
    truck, driver, trip = _setup_pickup_fixtures(db_session)
    service = TripTrackingService(db_session)

    # actual weight exactly equals truck capacity (5000 kg) -> Must be accepted
    req = RecordPickupRequest(
        actual_pickup_time=datetime(2026, 12, 1, 9, 30),
        handover_person="Nguyễn Văn Kho",
        actual_cargo_weight_kg=5000,
    )

    updated_trip = service.record_pickup(trip.id, req)
    assert updated_trip.status == TripStatus.PICKED_UP.value
    assert updated_trip.actual_cargo_weight_kg == 5000
