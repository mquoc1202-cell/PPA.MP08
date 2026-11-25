import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.trip import Trip, TripStatus
from src.models.booking import ResourceBooking, ResourceType, BookingStatus, ServiceType
from src.schemas.trip import AssignTripRequest, ReassignTripRequest
from src.services.dispatch_service import DispatchService
from src.core.exceptions import BusinessRuleViolationError, ScheduleConflictError


def _setup_lifecycle_fixtures(db: Session):
    truck1 = Truck(
        plate_number="51C-111.11",
        normalized_plate="51C11111",
        truck_type="Tải nhẹ 5T",
        capacity_kg=5000,
        status=TruckStatus.ACTIVE.value,
    )
    truck2 = Truck(
        plate_number="51C-222.22",
        normalized_plate="51C22222",
        truck_type="Tải trung 8T",
        capacity_kg=8000,
        status=TruckStatus.ACTIVE.value,
    )
    driver1 = Driver(
        driver_code="DRV001",
        full_name="Nguyen Van Mot",
        phone_number="0901111111",
        status=DriverStatus.ACTIVE.value,
    )
    driver2 = Driver(
        driver_code="DRV002",
        full_name="Tran Van Hai",
        phone_number="0902222222",
        status=DriverStatus.ACTIVE.value,
    )
    trip = Trip(
        reference_code="TRIP-LIFE-01",
        sender_name="CTY A",
        sender_phone="0911223344",
        pickup_address="KCN Tan Binh",
        delivery_address="KCN Song Than",
        cargo_type="Electronic Parts",
        cargo_weight_kg=4000,
        status=TripStatus.UNASSIGNED.value,
    )
    db.add_all([truck1, truck2, driver1, driver2, trip])
    db.commit()
    for obj in [truck1, truck2, driver1, driver2, trip]:
        db.refresh(obj)
    return truck1, truck2, driver1, driver2, trip


def test_reassign_trip_success(db_session: Session):
    truck1, truck2, driver1, driver2, trip = _setup_lifecycle_fixtures(db_session)
    service = DispatchService(db_session)

    start = datetime(2026, 12, 1, 8, 0)
    end = datetime(2026, 12, 1, 16, 0)

    # 1. Initial Assignment
    service.assign_trip(trip.id, AssignTripRequest(
        truck_id=truck1.id,
        driver_id=driver1.id,
        start_time=start,
        end_time=end,
    ))
    db_session.refresh(trip)
    assert trip.status == TripStatus.ASSIGNED.value
    assert trip.assigned_truck_id == truck1.id
    assert trip.assigned_driver_id == driver1.id

    # 2. Reassign to truck2 and driver2
    service.reassign_trip(trip.id, ReassignTripRequest(
        truck_id=truck2.id,
        driver_id=driver2.id,
        start_time=start,
        end_time=end,
    ))
    db_session.refresh(trip)
    assert trip.status == TripStatus.ASSIGNED.value
    assert trip.assigned_truck_id == truck2.id
    assert trip.assigned_driver_id == driver2.id

    # Verify old bookings are cancelled
    old_truck_bookings = db_session.query(ResourceBooking).filter(
        ResourceBooking.reference_code == trip.reference_code,
        ResourceBooking.resource_type == ResourceType.TRUCK.value,
        ResourceBooking.resource_id == truck1.id,
    ).all()
    assert all(b.status == BookingStatus.CANCELLED.value for b in old_truck_bookings)

    # Verify new bookings are confirmed
    new_truck_bookings = db_session.query(ResourceBooking).filter(
        ResourceBooking.reference_code == trip.reference_code,
        ResourceBooking.resource_type == ResourceType.TRUCK.value,
        ResourceBooking.resource_id == truck2.id,
        ResourceBooking.status == BookingStatus.CONFIRMED.value,
    ).all()
    assert len(new_truck_bookings) == 1


def test_reassign_conflict_keeps_original_state(db_session: Session):
    truck1, truck2, driver1, driver2, trip = _setup_lifecycle_fixtures(db_session)
    service = DispatchService(db_session)

    start = datetime(2026, 12, 1, 8, 0)
    end = datetime(2026, 12, 1, 16, 0)

    # Assign trip
    service.assign_trip(trip.id, AssignTripRequest(
        truck_id=truck1.id,
        driver_id=driver1.id,
        start_time=start,
        end_time=end,
    ))

    # Pre-occupy truck2 with another rental booking
    busy_booking = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck2.id,
        reference_code="OTHER-RENTAL",
        service_type=ServiceType.RENTAL.value,
        start_time=datetime(2026, 12, 1, 10, 0),
        end_time=datetime(2026, 12, 1, 14, 0),
        status=BookingStatus.CONFIRMED.value,
    )
    db_session.add(busy_booking)
    db_session.commit()

    # Attempt reassigning to truck2 -> Conflict!
    with pytest.raises(ScheduleConflictError):
        service.reassign_trip(trip.id, ReassignTripRequest(
            truck_id=truck2.id,
            driver_id=driver2.id,
            start_time=start,
            end_time=end,
        ))

    # Verify original truck1 booking is still CONFIRMED
    db_session.refresh(trip)
    assert trip.assigned_truck_id == truck1.id
    t1_booking = db_session.query(ResourceBooking).filter(
        ResourceBooking.reference_code == trip.reference_code,
        ResourceBooking.resource_type == ResourceType.TRUCK.value,
        ResourceBooking.resource_id == truck1.id,
    ).first()
    assert t1_booking.status == BookingStatus.CONFIRMED.value


def test_unassign_trip_success(db_session: Session):
    truck1, _, driver1, _, trip = _setup_lifecycle_fixtures(db_session)
    service = DispatchService(db_session)

    start = datetime(2026, 12, 1, 8, 0)
    end = datetime(2026, 12, 1, 16, 0)

    service.assign_trip(trip.id, AssignTripRequest(
        truck_id=truck1.id,
        driver_id=driver1.id,
        start_time=start,
        end_time=end,
    ))

    # Unassign
    service.unassign_trip(trip.id)
    db_session.refresh(trip)
    assert trip.status == TripStatus.UNASSIGNED.value
    assert trip.assigned_truck_id is None
    assert trip.assigned_driver_id is None
    assert trip.estimated_start_time is None
    assert trip.estimated_end_time is None

    # Check bookings cancelled
    bookings = db_session.query(ResourceBooking).filter(
        ResourceBooking.reference_code == trip.reference_code
    ).all()
    assert all(b.status == BookingStatus.CANCELLED.value for b in bookings)


def test_reassign_and_unassign_blocked_when_picked_up(db_session: Session):
    truck1, truck2, driver1, driver2, trip = _setup_lifecycle_fixtures(db_session)
    service = DispatchService(db_session)

    start = datetime(2026, 12, 1, 8, 0)
    end = datetime(2026, 12, 1, 16, 0)

    service.assign_trip(trip.id, AssignTripRequest(
        truck_id=truck1.id,
        driver_id=driver1.id,
        start_time=start,
        end_time=end,
    ))

    # Advance state to PICKED_UP
    trip.status = TripStatus.PICKED_UP.value
    db_session.commit()

    # Reassign attempt must fail
    with pytest.raises(BusinessRuleViolationError) as exc_info:
        service.reassign_trip(trip.id, ReassignTripRequest(
            truck_id=truck2.id,
            driver_id=driver2.id,
        ))
    assert "PICKED_UP" in str(exc_info.value)

    # Unassign attempt must fail
    with pytest.raises(BusinessRuleViolationError) as exc_info2:
        service.unassign_trip(trip.id)
    assert "ASSIGNED" in str(exc_info2.value)


def test_api_reassign_and_unassign_rbac(client: TestClient, db_session: Session, seed_test_users):
    truck1, truck2, driver1, driver2, trip = _setup_lifecycle_fixtures(db_session)
    service = DispatchService(db_session)

    start = datetime(2026, 12, 1, 8, 0)
    end = datetime(2026, 12, 1, 16, 0)
    service.assign_trip(trip.id, AssignTripRequest(
        truck_id=truck1.id,
        driver_id=driver1.id,
        start_time=start,
        end_time=end,
    ))

    # 1. Unauthenticated -> 401
    resp = client.post(f"/api/v1/trips/{trip.id}/reassign", json={"truck_id": truck2.id, "driver_id": driver2.id})
    assert resp.status_code == 401

    # 2. SAL role -> 403 Forbidden
    client.post("/api/v1/auth/login", json={"username": "sal_test", "password": "password123"})
    resp_sal = client.post(f"/api/v1/trips/{trip.id}/reassign", json={"truck_id": truck2.id, "driver_id": driver2.id})
    assert resp_sal.status_code == 403

    resp_sal_unassign = client.post(f"/api/v1/trips/{trip.id}/unassign")
    assert resp_sal_unassign.status_code == 403
    client.post("/api/v1/auth/logout")

    # 3. DSP role -> 200 OK
    client.post("/api/v1/auth/login", json={"username": "dsp_test", "password": "password123"})
    resp_dsp = client.post(f"/api/v1/trips/{trip.id}/reassign", json={"truck_id": truck2.id, "driver_id": driver2.id})
    assert resp_dsp.status_code == 200
    assert resp_dsp.json()["data"]["assigned_truck_id"] == truck2.id

    # DSP unassign -> 200 OK
    resp_dsp_unassign = client.post(f"/api/v1/trips/{trip.id}/unassign")
    assert resp_dsp_unassign.status_code == 200
    assert resp_dsp_unassign.json()["data"]["status"] == "UNASSIGNED"
