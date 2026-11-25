from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session
from src.models.trip import Trip, TripStatus
from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.booking import ResourceBooking, ResourceType, BookingStatus, ServiceType
from src.models.trip_event import TripEvent, TripEventType
from src.services.incident_service import IncidentService
from src.repositories.booking_repo import ResourceBookingRepository
from src.core.exceptions import BusinessRuleException, NotFoundException


def setup_resources_and_trip(db: Session):
    """Helper to set up truck, driver, and active trip with bookings."""
    now = datetime.now(timezone.utc)
    truck = Truck(
        plate_number="29C-888.88",
        normalized_plate="29C88888",
        truck_type="Tải thùng",
        capacity_kg=5000,
        status=TruckStatus.ACTIVE.value,
    )
    driver = Driver(
        driver_code="DRV-8888",
        full_name="Trần Văn Tài Xế",
        phone_number="0988888888",
        status=DriverStatus.ACTIVE.value,
    )
    db.add_all([truck, driver])
    db.commit()
    db.refresh(truck)
    db.refresh(driver)

    trip_a = Trip(
        reference_code=f"TRIP-A-{now.timestamp()}",
        sender_name="Cong ty A",
        sender_phone="0911111111",
        pickup_address="Kho A",
        delivery_address="Kho B",
        cargo_weight_kg=4000,
        cargo_type="May moc",
        status=TripStatus.IN_TRANSIT.value,
        assigned_truck_id=truck.id,
        assigned_driver_id=driver.id,
        estimated_start_time=now - timedelta(hours=3),
        estimated_end_time=now + timedelta(hours=2),
    )
    db.add(trip_a)
    db.commit()
    db.refresh(trip_a)

    booking_a_truck = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code=trip_a.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=trip_a.estimated_start_time,
        end_time=trip_a.estimated_end_time,
        status=BookingStatus.IN_PROGRESS.value,
    )
    booking_a_driver = ResourceBooking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver.id,
        reference_code=trip_a.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=trip_a.estimated_start_time,
        end_time=trip_a.estimated_end_time,
        status=BookingStatus.IN_PROGRESS.value,
    )
    db.add_all([booking_a_truck, booking_a_driver])
    db.commit()

    return truck, driver, trip_a


def test_reschedule_success_without_conflicts(db_session: Session):
    """Test extending estimated_end_time successfully when no future bookings exist."""
    service = IncidentService(db_session)
    truck, driver, trip = setup_resources_and_trip(db_session)

    new_end_time = trip.estimated_end_time + timedelta(hours=2)
    updated_trip, conflicts = service.reschedule_trip(
        trip_id=trip.id,
        new_estimated_end_time=new_end_time,
        reason="Kẹt xe cao tốc",
        user_id=1,
    )

    assert updated_trip.estimated_end_time == new_end_time
    assert len(conflicts) == 0

    # Verify ResourceBooking end_time was updated
    bookings = (
        db_session.query(ResourceBooking)
        .filter(ResourceBooking.reference_code == trip.reference_code)
        .all()
    )
    assert len(bookings) == 2
    for b in bookings:
        assert b.end_time == new_end_time

    # Verify TripEvent audit trail
    event = (
        db_session.query(TripEvent)
        .filter(TripEvent.trip_id == trip.id, TripEvent.event_type == TripEventType.SCHEDULE_DELAYED.value)
        .first()
    )
    assert event is not None
    assert "Kẹt xe cao tốc" in event.notes


def test_reschedule_before_start_time_rejection(db_session: Session):
    """Test rescheduling new end time earlier than estimated_start_time raises BusinessRuleException."""
    service = IncidentService(db_session)
    truck, driver, trip = setup_resources_and_trip(db_session)

    invalid_end_time = trip.estimated_start_time - timedelta(hours=1)
    with pytest.raises(BusinessRuleException):
        service.reschedule_trip(trip.id, invalid_end_time, "Lỗi giờ", user_id=1)


def test_reschedule_with_future_conflicts_detection(db_session: Session):
    """
    Test User Story 3 & BR-09:
    When rescheduling overlaps with a future booking, the system keeps the current trip updated,
    extends its bookings, and returns the list of conflicting future bookings for DSP alerting.
    """
    service = IncidentService(db_session)
    truck, driver, trip_a = setup_resources_and_trip(db_session)

    # Create a future booking for the same truck (e.g. TRIP-B or RENTAL) starting at old_end_time + 1h
    future_start = trip_a.estimated_end_time + timedelta(hours=1)
    future_end = future_start + timedelta(hours=4)
    future_booking = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code="ORDER-2026-FUT999",
        service_type=ServiceType.RENTAL.value,
        start_time=future_start,
        end_time=future_end,
        status=BookingStatus.CONFIRMED.value,
    )
    db_session.add(future_booking)
    db_session.commit()

    # Now reschedule trip_a to extend past future_start (overlap with future booking)
    rescheduled_end = future_start + timedelta(hours=2)  # Overlaps!
    updated_trip, conflicts = service.reschedule_trip(
        trip_id=trip_a.id,
        new_estimated_end_time=rescheduled_end,
        reason="Hỏng lốp và tắc phà",
        user_id=1,
    )

    # Trip A is updated to reflect reality
    assert updated_trip.estimated_end_time == rescheduled_end
    # System detects the conflict
    assert len(conflicts) >= 1
    conflict_ref_codes = [c.reference_code for c in conflicts]
    assert "ORDER-2026-FUT999" in conflict_ref_codes


def test_reschedule_br09_busy_resource_blocks_subsequent_trip(db_session: Session):
    """
    Test User Story 3 invariant (BR-09):
    A resource currently busy in an in-progress booking cannot start/pickup a new trip.
    """
    truck, driver, trip_a = setup_resources_and_trip(db_session)
    booking_repo = ResourceBookingRepository(db_session)

    # Truck and driver are IN_PROGRESS for trip_a
    is_truck_busy = booking_repo.has_in_progress_booking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        exclude_reference_code="ANOTHER-TRIP",
    )
    assert is_truck_busy is True

    is_driver_busy = booking_repo.has_in_progress_booking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver.id,
        exclude_reference_code="ANOTHER-TRIP",
    )
    assert is_driver_busy is True
