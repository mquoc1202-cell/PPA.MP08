import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.trip import Trip, TripStatus


@pytest.fixture
def api_test_data(db_session: Session):
    """Seed test truck, driver, and trip for contract testing."""
    truck = Truck(
        plate_number="51D-777.77",
        normalized_plate="51D77777",
        truck_type="Xe tải 8T",
        capacity_kg=8000,
        status=TruckStatus.ACTIVE.value,
    )
    driver = Driver(
        driver_code="TX777",
        full_name="Trần Văn Hợp Đồng",
        phone_number="0977777777",
        status=DriverStatus.ACTIVE.value,
    )
    trip = Trip(
        reference_code="TRIP-CONTRACT-01",
        sender_name="Công ty Khách Hàng",
        sender_phone="0911333444",
        pickup_address="Kho Sài Gòn",
        delivery_address="Kho Bình Dương",
        cargo_weight_kg=5500,
        cargo_type="Hàng gia công",
        status=TripStatus.UNASSIGNED.value,
    )
    db_session.add_all([truck, driver, trip])
    db_session.flush()
    return {"truck": truck, "driver": driver, "trip": trip}


def test_trips_api_contract_lifecycle(client: TestClient, seed_test_users, api_test_data):
    """Test trips listing, creation, and dispatch assign matching contracts/trips-api.yaml."""
    # 1. Login as DSP
    client.post("/api/v1/auth/login", json={"username": "dsp_test", "password": "password123"})

    # 2. GET /api/v1/trips -> 200
    res_list = client.get("/api/v1/trips")
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["success"] is True
    assert len(data["data"]) >= 1

    # 3. POST /api/v1/trips -> 201 Created
    res_create = client.post("/api/v1/trips", json={
        "sender_name": "Công ty Sản Xuất Bao Bì",
        "sender_phone": "0988112233",
        "pickup_address": "KCN Tân Bình, TP.HCM",
        "delivery_address": "KCN Sóng Thần, Bình Dương",
        "cargo_weight_kg": 3500,
        "cargo_type": "Bao bì nhựa",
        "notes": "Giao trong giờ hành chính"
    })
    assert res_create.status_code == 201
    created_trip = res_create.json()["data"]
    assert created_trip["status"] == "UNASSIGNED"
    trip_id = created_trip["id"]

    # 4. POST /api/v1/trips/{id}/assign with valid params -> 200 OK
    truck = api_test_data["truck"]
    driver = api_test_data["driver"]
    now = datetime.now(timezone.utc)
    start_time = (now + timedelta(days=1)).isoformat()
    end_time = (now + timedelta(days=2)).isoformat()

    res_assign = client.post(f"/api/v1/trips/{trip_id}/assign", json={
        "truck_id": truck.id,
        "driver_id": driver.id,
        "start_time": start_time,
        "end_time": end_time
    })
    assert res_assign.status_code == 200
    assigned_data = res_assign.json()["data"]
    assert assigned_data["status"] == "ASSIGNED"
    assert assigned_data["assigned_truck_id"] == truck.id
    assert assigned_data["assigned_driver_id"] == driver.id
