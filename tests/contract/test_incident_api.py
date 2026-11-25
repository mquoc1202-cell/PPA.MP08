import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.models.trip import Trip, TripStatus
from src.models.user import User


def get_auth_cookie(client: TestClient, username: str = "dsp_test", password: str = "password123") -> dict:
    """Helper to login and obtain session cookie."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.cookies


def create_api_trip(db: Session, status: str = TripStatus.IN_TRANSIT.value) -> Trip:
    """Helper to seed trip for API testing."""
    now = datetime.now(timezone.utc)
    trip = Trip(
        reference_code=f"TRIP-API-{now.timestamp()}",
        sender_name="Cong ty TNHH API Test",
        sender_phone="0987654321",
        pickup_address="Kho Tong Ha Noi",
        delivery_address="Kho Chi Nhanh Da Nang",
        cargo_weight_kg=2500,
        cargo_type="Linh kien dien tu",
        status=status,
        estimated_start_time=now - timedelta(hours=2),
        estimated_end_time=now + timedelta(hours=6),
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


def test_incident_api_contract_lifecycle(client: TestClient, db_session: Session, seed_test_users):
    """Test full API contract for creating, listing, and resolving trip issues."""
    cookies = get_auth_cookie(client, "dsp_test", "password123")
    trip = create_api_trip(db_session)

    # 1. POST /api/v1/trips/{id}/issues (Create issue)
    create_payload = {
        "issue_type": "VEHICLE_BREAKDOWN",
        "description": "Xe bi hong he thong lam mat dong co",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "handled_by": "Gara oto Ha Dong",
        "estimated_resolution_time": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
    }
    res_create = client.post(f"/api/v1/trips/{trip.id}/issues", json=create_payload, cookies=cookies)
    assert res_create.status_code == 201
    json_create = res_create.json()
    assert json_create["success"] is True
    issue_data = json_create["data"]
    assert issue_data["issue_type"] == "VEHICLE_BREAKDOWN"
    assert issue_data["status"] == "OPEN"
    issue_id = issue_data["id"]

    # 2. GET /api/v1/trips/{id}/issues (List issues)
    res_list = client.get(f"/api/v1/trips/{trip.id}/issues", cookies=cookies)
    assert res_list.status_code == 200
    json_list = res_list.json()
    assert json_list["success"] is True
    assert len(json_list["data"]) >= 1
    assert any(i["id"] == issue_id for i in json_list["data"])

    # 3. POST /api/v1/trips/{id}/issues/{issue_id}/resolve (Resolve issue)
    resolve_payload = {
        "resolution_notes": "Gara da thay xong ket nuoc lam mat, dong co hoat dong binh thuong"
    }
    res_resolve = client.post(
        f"/api/v1/trips/{trip.id}/issues/{issue_id}/resolve",
        json=resolve_payload,
        cookies=cookies,
    )
    assert res_resolve.status_code == 200
    json_resolve = res_resolve.json()
    assert json_resolve["success"] is True
    assert json_resolve["data"]["status"] == "RESOLVED"
    assert json_resolve["data"]["resolution_notes"] == resolve_payload["resolution_notes"]


def test_reschedule_api_contract_and_conflict_handling(client: TestClient, db_session: Session, seed_test_users):
    """Test API contract for rescheduling trip (POST /api/v1/trips/{id}/reschedule) with and without conflicts."""
    from src.models.truck import Truck, TruckStatus
    from src.models.driver import Driver, DriverStatus
    from src.models.booking import ResourceBooking, ResourceType, BookingStatus, ServiceType

    cookies = get_auth_cookie(client, "dsp_test", "password123")

    now = datetime.now(timezone.utc)
    truck = Truck(
        plate_number="29C-999.99",
        normalized_plate="29C99999",
        truck_type="Tải thùng",
        capacity_kg=5000,
        status=TruckStatus.ACTIVE.value,
    )
    driver = Driver(
        driver_code="DRV-9999",
        full_name="Lê Văn Tài",
        phone_number="0977777777",
        status=DriverStatus.ACTIVE.value,
    )
    db_session.add_all([truck, driver])
    db_session.commit()
    db_session.refresh(truck)
    db_session.refresh(driver)

    trip = Trip(
        reference_code=f"TRIP-RESCHED-{now.timestamp()}",
        sender_name="Cong ty TNHH Reschedule Test",
        sender_phone="0987654321",
        pickup_address="Kho A",
        delivery_address="Kho B",
        cargo_weight_kg=2500,
        cargo_type="May tinh",
        status=TripStatus.IN_TRANSIT.value,
        assigned_truck_id=truck.id,
        assigned_driver_id=driver.id,
        estimated_start_time=now - timedelta(hours=2),
        estimated_end_time=now + timedelta(hours=4),
    )
    db_session.add(trip)
    db_session.commit()
    db_session.refresh(trip)

    booking_truck = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code=trip.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=trip.estimated_start_time,
        end_time=trip.estimated_end_time,
        status=BookingStatus.IN_PROGRESS.value,
    )
    db_session.add(booking_truck)
    db_session.commit()

    # 1. Reschedule without conflict -> 200 OK
    resched_time_1 = trip.estimated_end_time + timedelta(hours=1)
    res_1 = client.post(
        f"/api/v1/trips/{trip.id}/reschedule",
        json={"new_estimated_end_time": resched_time_1.isoformat(), "reason": "Kẹt xe cầu Thanh Trì"},
        cookies=cookies,
    )
    assert res_1.status_code == 200
    json_1 = res_1.json()
    assert json_1["success"] is True
    assert json_1["data"]["has_conflicts"] is False
    assert len(json_1["data"]["conflicts"]) == 0

    # 2. Add future booking for the truck that starts soon
    future_start = resched_time_1 + timedelta(hours=1)
    future_end = future_start + timedelta(hours=3)
    future_booking = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code="ORDER-FUT-9999",
        service_type=ServiceType.RENTAL.value,
        start_time=future_start,
        end_time=future_end,
        status=BookingStatus.CONFIRMED.value,
    )
    db_session.add(future_booking)
    db_session.commit()

    # 3. Reschedule with overlap -> 409 Conflict
    resched_time_2 = future_start + timedelta(hours=2)
    res_2 = client.post(
        f"/api/v1/trips/{trip.id}/reschedule",
        json={"new_estimated_end_time": resched_time_2.isoformat(), "reason": "Sửa chữa xe trên đường"},
        cookies=cookies,
    )
    assert res_2.status_code == 409
    json_2 = res_2.json()
    assert json_2["data"]["has_conflicts"] is True
    assert len(json_2["data"]["conflicts"]) >= 1
    assert any(c["reference_code"] == "ORDER-FUT-9999" for c in json_2["data"]["conflicts"])
