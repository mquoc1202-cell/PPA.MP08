import pytest
import io
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.trip import Trip, TripStatus
from src.models.booking import ResourceBooking, ResourceType, BookingStatus, ServiceType


def test_delivery_api_contract_lifecycle(client: TestClient, db_session, seed_test_users):
    # 1. Setup Truck, Driver, Trip in IN_TRANSIT
    truck = Truck(
        plate_number="51C-API.DELIV",
        normalized_plate="51CAPIDELIV",
        truck_type="Tải 5T",
        capacity_kg=5000,
        status=TruckStatus.ACTIVE.value,
    )
    driver = Driver(
        driver_code="DRV_API_DELIV",
        full_name="Tài Xế API",
        phone_number="0911223344",
        status=DriverStatus.ACTIVE.value,
    )
    db_session.add_all([truck, driver])
    db_session.commit()
    db_session.refresh(truck)
    db_session.refresh(driver)

    now = datetime.now()
    trip = Trip(
        reference_code="TRIP-API-DELIV-01",
        sender_name="Công ty Giao Nhận API",
        sender_phone="0912345678",
        pickup_address="Kho Xuất Phát",
        delivery_address="Kho Đích",
        cargo_type="Hàng Đóng Thùng",
        cargo_weight_kg=3000,
        status=TripStatus.IN_TRANSIT.value,
        assigned_truck_id=truck.id,
        assigned_driver_id=driver.id,
        actual_pickup_time=now - timedelta(hours=3),
        actual_depart_time=now - timedelta(hours=2),
    )
    db_session.add(trip)
    db_session.commit()
    db_session.refresh(trip)

    # Add in-progress bookings
    b_truck = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code=trip.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=now - timedelta(hours=3),
        end_time=now + timedelta(hours=3),
        status=BookingStatus.IN_PROGRESS.value,
    )
    b_driver = ResourceBooking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver.id,
        reference_code=trip.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=now - timedelta(hours=3),
        end_time=now + timedelta(hours=3),
        status=BookingStatus.IN_PROGRESS.value,
    )
    db_session.add_all([b_truck, b_driver])
    db_session.commit()

    # Login as DSP
    login_res = client.post("/api/v1/auth/login", json={"username": "dsp_test", "password": "password123"})
    assert login_res.status_code == 200

    # 2. Test POST /api/v1/trips/{id}/deliver (SUCCESS with file)
    deliv_time = (now - timedelta(minutes=30)).isoformat()
    pdf_content = b"%PDF-1.4 Mock PDF content"
    files = [
        ("evidence_files", ("bien_ban_pod.pdf", io.BytesIO(pdf_content), "application/pdf"))
    ]
    data = {
        "actual_delivery_time": deliv_time,
        "recipient_name": "Người Nhận API Test",
        "result": "SUCCESS",
        "delivery_notes": "Giao đủ hàng qua API",
    }

    deliver_res = client.post(f"/api/v1/trips/{trip.id}/deliver", data=data, files=files)
    assert deliver_res.status_code == 200
    res_json = deliver_res.json()
    assert res_json["success"] is True
    assert res_json["data"]["status"] == TripStatus.DELIVERED.value
    assert res_json["data"]["recipient_name"] == "Người Nhận API Test"

    # 3. Test GET /api/v1/trips/{id}/evidence
    evidence_res = client.get(f"/api/v1/trips/{trip.id}/evidence")
    assert evidence_res.status_code == 200
    evidence_json = evidence_res.json()
    assert evidence_json["success"] is True
    assert len(evidence_json["data"]) == 1
    evidence_id = evidence_json["data"][0]["id"]
    assert evidence_json["data"][0]["file_name"] == "bien_ban_pod.pdf"

    # 4. Test GET /api/v1/trips/{id}/evidence/{evidence_id}/download
    download_res = client.get(f"/api/v1/trips/{trip.id}/evidence/{evidence_id}/download")
    assert download_res.status_code == 200
    assert download_res.content == pdf_content

    # 5. Test POST /api/v1/trips/{id}/complete
    complete_time = (now - timedelta(minutes=10)).isoformat()
    complete_res = client.post(
        f"/api/v1/trips/{trip.id}/complete",
        json={
            "actual_completed_time": complete_time,
            "notes": "Đóng chuyến hoàn tất qua API",
        },
    )
    assert complete_res.status_code == 200
    complete_json = complete_res.json()
    assert complete_json["success"] is True
    assert complete_json["data"]["status"] == TripStatus.COMPLETED.value
