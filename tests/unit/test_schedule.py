import pytest
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.booking import ResourceBooking, ResourceType, BookingStatus, ServiceType
from src.repositories.booking_repo import ResourceBookingRepository


def _setup_schedule_fixtures(db: Session):
    truck = Truck(
        plate_number="51C-SCHED.01",
        normalized_plate="51CSCHED01",
        truck_type="Tải trung 8T",
        capacity_kg=8000,
        status=TruckStatus.ACTIVE.value,
    )
    driver = Driver(
        driver_code="DRV_S01",
        full_name="Driver Schedule Tester",
        phone_number="0988000111",
        status=DriverStatus.ACTIVE.value,
    )
    db.add_all([truck, driver])
    db.commit()
    db.refresh(truck)
    db.refresh(driver)

    # Booking 1: Day 1 (Freight)
    b1 = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code="TRIP-SCHED-01",
        service_type=ServiceType.FREIGHT.value,
        start_time=datetime(2026, 12, 10, 8, 0),
        end_time=datetime(2026, 12, 10, 16, 0),
        status=BookingStatus.CONFIRMED.value,
    )
    # Booking 2: Day 3 (Rental)
    b2 = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code="RENTAL-SCHED-01",
        service_type=ServiceType.RENTAL.value,
        start_time=datetime(2026, 12, 12, 9, 0),
        end_time=datetime(2026, 12, 12, 17, 0),
        status=BookingStatus.CONFIRMED.value,
    )
    # Driver Booking: Day 1
    b3 = ResourceBooking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver.id,
        reference_code="TRIP-SCHED-01",
        service_type=ServiceType.FREIGHT.value,
        start_time=datetime(2026, 12, 10, 8, 0),
        end_time=datetime(2026, 12, 10, 16, 0),
        status=BookingStatus.CONFIRMED.value,
    )
    db.add_all([b1, b2, b3])
    db.commit()
    return truck, driver


def test_schedule_repository_date_range(db_session: Session):
    truck, driver = _setup_schedule_fixtures(db_session)
    repo = ResourceBookingRepository(db_session)

    # 1. Query all bookings for truck
    all_truck_bookings = repo.get_bookings_by_range(ResourceType.TRUCK.value, truck.id)
    assert len(all_truck_bookings) == 2

    # 2. Query date range matching only Day 1
    day1_bookings = repo.get_bookings_by_range(
        ResourceType.TRUCK.value,
        truck.id,
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 10),
    )
    assert len(day1_bookings) == 1
    assert day1_bookings[0].reference_code == "TRIP-SCHED-01"

    # 3. Query date range matching only Day 3
    day3_bookings = repo.get_bookings_by_range(
        ResourceType.TRUCK.value,
        truck.id,
        start_date=date(2026, 12, 12),
        end_date=date(2026, 12, 12),
    )
    assert len(day3_bookings) == 1
    assert day3_bookings[0].reference_code == "RENTAL-SCHED-01"

    # 4. Query driver bookings
    driver_bookings = repo.get_bookings_by_range(ResourceType.DRIVER.value, driver.id)
    assert len(driver_bookings) == 1
    assert driver_bookings[0].reference_code == "TRIP-SCHED-01"


def test_api_schedule_endpoints(client: TestClient, db_session: Session, seed_test_users):
    truck, driver = _setup_schedule_fixtures(db_session)

    # 1. Unauthenticated -> 401
    resp_unauth = client.get(f"/api/v1/schedule/trucks/{truck.id}")
    assert resp_unauth.status_code == 401

    # 2. Login as DSP or SAL
    client.post("/api/v1/auth/login", json={"username": "sal_test", "password": "password123"})

    # 3. Truck schedule lookup
    resp = client.get(f"/api/v1/schedule/trucks/{truck.id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2

    # 4. Truck schedule with date filter
    resp_filtered = client.get(f"/api/v1/schedule/trucks/{truck.id}?start_date=2026-12-10&end_date=2026-12-10")
    assert resp_filtered.status_code == 200
    data_filtered = resp_filtered.json()["data"]
    assert len(data_filtered) == 1
    assert data_filtered[0]["reference_code"] == "TRIP-SCHED-01"

    # 5. Driver schedule lookup
    resp_drv = client.get(f"/api/v1/schedule/drivers/{driver.id}")
    assert resp_drv.status_code == 200
    assert len(resp_drv.json()["data"]) == 1

    # 6. Non-existent truck -> 404
    resp_404 = client.get("/api/v1/schedule/trucks/999999")
    assert resp_404.status_code == 404


def test_web_schedule_view(client: TestClient, db_session: Session, seed_test_users):
    truck, driver = _setup_schedule_fixtures(db_session)

    # 1. Login
    client.post("/api/v1/auth/login", json={"username": "dsp_test", "password": "password123"})

    # 2. GET /schedule for truck
    resp_truck = client.get(f"/schedule?resource_type=truck&resource_id={truck.id}")
    assert resp_truck.status_code == 200
    assert truck.plate_number in resp_truck.text
    assert "TRIP-SCHED-01" in resp_truck.text

    # 3. GET /schedule for driver
    resp_drv = client.get(f"/schedule?resource_type=driver&resource_id={driver.id}")
    assert resp_drv.status_code == 200
    assert driver.full_name in resp_drv.text
    assert "TRIP-SCHED-01" in resp_drv.text
