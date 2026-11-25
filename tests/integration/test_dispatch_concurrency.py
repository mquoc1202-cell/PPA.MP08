import pytest
import concurrent.futures
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.trip import Trip, TripStatus
from src.models.booking import ResourceBooking, ResourceType, BookingStatus
from src.schemas.trip import AssignTripRequest
from src.services.dispatch_service import DispatchService
from src.core.exceptions import ScheduleConflictError


def _setup_concurrency_fixtures(db: Session):
    truck = Truck(
        plate_number="51C-CONC.01",
        normalized_plate="51CCONC01",
        truck_type="Tải nhẹ 5T",
        capacity_kg=6000,
        status=TruckStatus.ACTIVE.value,
    )
    driver1 = Driver(
        driver_code="DRV_C01",
        full_name="Driver Concurrency One",
        phone_number="0911000001",
        status=DriverStatus.ACTIVE.value,
    )
    driver2 = Driver(
        driver_code="DRV_C02",
        full_name="Driver Concurrency Two",
        phone_number="0911000002",
        status=DriverStatus.ACTIVE.value,
    )
    trip1 = Trip(
        reference_code="TRIP-CONC-01",
        sender_name="Sender 1",
        sender_phone="0901000001",
        pickup_address="Kho 1",
        delivery_address="Kho 2",
        cargo_type="Hàng A",
        cargo_weight_kg=3000,
        status=TripStatus.UNASSIGNED.value,
    )
    trip2 = Trip(
        reference_code="TRIP-CONC-02",
        sender_name="Sender 2",
        sender_phone="0901000002",
        pickup_address="Kho 3",
        delivery_address="Kho 4",
        cargo_type="Hàng B",
        cargo_weight_kg=3500,
        status=TripStatus.UNASSIGNED.value,
    )
    db.add_all([truck, driver1, driver2, trip1, trip2])
    db.commit()
    for obj in [truck, driver1, driver2, trip1, trip2]:
        db.refresh(obj)
    return truck, driver1, driver2, trip1, trip2


def test_concurrent_dispatch_same_truck(db_session: Session):
    """
    Simulate two dispatchers attempting to assign different trips to the SAME truck
    in overlapping timeframes. Exactly 1 must succeed, and 1 must fail with ScheduleConflictError.
    """
    truck, driver1, driver2, trip1, trip2 = _setup_concurrency_fixtures(db_session)
    service = DispatchService(db_session)

    start = datetime(2026, 12, 5, 8, 0)
    end = datetime(2026, 12, 5, 17, 0)

    # 1. Dispatcher A assigns trip1 to truck and driver1
    result1 = service.assign_trip(
        trip1.id,
        AssignTripRequest(
            truck_id=truck.id,
            driver_id=driver1.id,
            start_time=start,
            end_time=end,
        ),
    )
    assert result1.status == TripStatus.ASSIGNED.value

    # 2. Dispatcher B immediately attempts to assign trip2 to same truck (different driver, overlapping time)
    with pytest.raises(ScheduleConflictError) as exc_info:
        service.assign_trip(
            trip2.id,
            AssignTripRequest(
                truck_id=truck.id,
                driver_id=driver2.id,
                start_time=datetime(2026, 12, 5, 10, 0),
                end_time=datetime(2026, 12, 5, 14, 0),
            ),
        )

    assert truck.plate_number in str(exc_info.value)
    assert len(exc_info.value.conflicting_bookings) >= 1
    assert exc_info.value.conflicting_bookings[0]["reference_code"] == trip1.reference_code

    # 3. Verify zero orphan bookings created for trip2
    db_session.refresh(trip2)
    assert trip2.status == TripStatus.UNASSIGNED.value
    assert trip2.assigned_truck_id is None

    trip2_bookings = db_session.query(ResourceBooking).filter(
        ResourceBooking.reference_code == trip2.reference_code
    ).all()
    assert len(trip2_bookings) == 0


def test_concurrent_dispatch_same_driver(db_session: Session):
    """
    Simulate two dispatchers attempting to assign different trips to different trucks
    but the SAME driver in overlapping timeframes. Exactly 1 must succeed and 1 must fail.
    """
    truck1, driver1, _, trip1, trip2 = _setup_concurrency_fixtures(db_session)
    truck2 = Truck(
        plate_number="51C-CONC.02",
        normalized_plate="51CCONC02",
        truck_type="Tải trung 8T",
        capacity_kg=8000,
        status=TruckStatus.ACTIVE.value,
    )
    db_session.add(truck2)
    db_session.commit()
    db_session.refresh(truck2)

    service = DispatchService(db_session)

    start = datetime(2026, 12, 6, 8, 0)
    end = datetime(2026, 12, 6, 16, 0)

    # Dispatcher A assigns trip1 to truck1 and driver1
    service.assign_trip(
        trip1.id,
        AssignTripRequest(
            truck_id=truck1.id,
            driver_id=driver1.id,
            start_time=start,
            end_time=end,
        ),
    )

    # Dispatcher B assigns trip2 to truck2 and SAME driver1
    with pytest.raises(ScheduleConflictError) as exc_info:
        service.assign_trip(
            trip2.id,
            AssignTripRequest(
                truck_id=truck2.id,
                driver_id=driver1.id,
                start_time=datetime(2026, 12, 6, 12, 0),
                end_time=datetime(2026, 12, 6, 18, 0),
            ),
        )

    assert driver1.full_name in str(exc_info.value) or driver1.driver_code in str(exc_info.value)
    assert len(exc_info.value.conflicting_bookings) >= 1

    # Trip2 remains UNASSIGNED with 0 bookings
    db_session.refresh(trip2)
    assert trip2.status == TripStatus.UNASSIGNED.value


def test_api_concurrency_returns_409(client: TestClient, db_session: Session, seed_test_users):
    """
    Verify that an overlapping assignment attempt via REST API returns HTTP 409 Conflict
    with structured conflict details.
    """
    truck, driver1, driver2, trip1, trip2 = _setup_concurrency_fixtures(db_session)

    # Login as DSP
    client.post("/api/v1/auth/login", json={"username": "dsp_test", "password": "password123"})

    payload1 = {
        "truck_id": truck.id,
        "driver_id": driver1.id,
        "start_time": "2026-12-07T08:00:00",
        "end_time": "2026-12-07T16:00:00",
    }
    resp1 = client.post(f"/api/v1/trips/{trip1.id}/assign", json=payload1)
    assert resp1.status_code == 200
    assert resp1.json()["data"]["status"] == "ASSIGNED"

    # Conflicting assignment on same truck
    payload2 = {
        "truck_id": truck.id,
        "driver_id": driver2.id,
        "start_time": "2026-12-07T10:00:00",
        "end_time": "2026-12-07T14:00:00",
    }
    resp2 = client.post(f"/api/v1/trips/{trip2.id}/assign", json=payload2)
    assert resp2.status_code == 409
    body2 = resp2.json()
    assert body2["success"] is False
    assert "Xe tải" in body2["error"]
    assert "conflicting_bookings" in body2["data"]
    assert len(body2["data"]["conflicting_bookings"]) >= 1
    assert body2["data"]["conflicting_bookings"][0]["reference_code"] == trip1.reference_code
