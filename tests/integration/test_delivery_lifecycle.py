import pytest
import io
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.trip import Trip, TripStatus
from src.models.booking import ResourceBooking, ResourceType, BookingStatus, ServiceType
from src.repositories.booking_repo import ResourceBookingRepository


def test_delivery_and_resource_release_lifecycle(client: TestClient, db_session, seed_test_users):
    truck = Truck(
        plate_number="51C-REL.01",
        normalized_plate="51CREL01",
        truck_type="Tải 8T",
        capacity_kg=8000,
        status=TruckStatus.ACTIVE.value,
    )
    driver = Driver(
        driver_code="DRV_REL01",
        full_name="Tài Xế Giải Phóng",
        phone_number="0911777888",
        status=DriverStatus.ACTIVE.value,
    )
    db_session.add_all([truck, driver])
    db_session.commit()
    db_session.refresh(truck)
    db_session.refresh(driver)

    now = datetime.now()
    trip1 = Trip(
        reference_code="TRIP-REL-01",
        sender_name="Kho Tổng Hóa Chất",
        sender_phone="0911222333",
        pickup_address="Kho A",
        delivery_address="Kho B",
        cargo_type="Hàng hóa",
        cargo_weight_kg=5000,
        status=TripStatus.IN_TRANSIT.value,
        assigned_truck_id=truck.id,
        assigned_driver_id=driver.id,
        actual_pickup_time=now - timedelta(hours=3),
        actual_depart_time=now - timedelta(hours=2),
    )
    db_session.add(trip1)
    db_session.commit()
    db_session.refresh(trip1)

    b_truck1 = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code=trip1.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=now - timedelta(hours=3),
        end_time=now + timedelta(hours=3),
        status=BookingStatus.IN_PROGRESS.value,
    )
    b_driver1 = ResourceBooking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver.id,
        reference_code=trip1.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=now - timedelta(hours=3),
        end_time=now + timedelta(hours=3),
        status=BookingStatus.IN_PROGRESS.value,
    )
    db_session.add_all([b_truck1, b_driver1])
    db_session.commit()

    booking_repo = ResourceBookingRepository(db_session)
    # Resource is currently busy with in-progress booking
    assert booking_repo.has_in_progress_booking(ResourceType.TRUCK.value, truck.id) is True
    assert booking_repo.has_in_progress_booking(ResourceType.DRIVER.value, driver.id) is True

    # Login as DSP
    client.post("/api/v1/auth/login", json={"username": "dsp_test", "password": "password123"})

    # 1. Deliver trip1
    pdf_content = b"%PDF-1.4 POD Evidence"
    files = [("evidence_files", ("pod.pdf", io.BytesIO(pdf_content), "application/pdf"))]
    deliv_res = client.post(
        f"/api/v1/trips/{trip1.id}/deliver",
        data={
            "actual_delivery_time": (now - timedelta(minutes=40)).isoformat(),
            "recipient_name": "Người Nhận Hàng",
            "result": "SUCCESS",
        },
        files=files,
    )
    assert deliv_res.status_code == 200

    # Resource still IN_PROGRESS until completed
    assert booking_repo.has_in_progress_booking(ResourceType.TRUCK.value, truck.id) is True

    # 2. Complete trip1
    comp_res = client.post(
        f"/api/v1/trips/{trip1.id}/complete",
        json={"actual_completed_time": (now - timedelta(minutes=10)).isoformat()},
    )
    assert comp_res.status_code == 200

    # Resource is now COMPLETED and released!
    db_session.expire_all()
    assert booking_repo.has_in_progress_booking(ResourceType.TRUCK.value, truck.id) is False
    assert booking_repo.has_in_progress_booking(ResourceType.DRIVER.value, driver.id) is False


def test_delivery_failure_incident_lifecycle(client: TestClient, db_session, seed_test_users):
    truck = Truck(
        plate_number="51C-FAIL.01",
        normalized_plate="51CFAIL01",
        truck_type="Tải 5T",
        capacity_kg=5000,
        status=TruckStatus.ACTIVE.value,
    )
    driver = Driver(
        driver_code="DRV_FAIL01",
        full_name="Tài Xế Sự Cố",
        phone_number="0911000111",
        status=DriverStatus.ACTIVE.value,
    )
    db_session.add_all([truck, driver])
    db_session.commit()
    db_session.refresh(truck)
    db_session.refresh(driver)

    now = datetime.now()
    trip = Trip(
        reference_code="TRIP-FAIL-01",
        sender_name="Kho Hàng Sự Cố",
        sender_phone="0911999888",
        pickup_address="Kho Đi",
        delivery_address="Kho Đến",
        cargo_type="Hàng dễ vỡ",
        cargo_weight_kg=2000,
        status=TripStatus.IN_TRANSIT.value,
        assigned_truck_id=truck.id,
        assigned_driver_id=driver.id,
        actual_pickup_time=now - timedelta(hours=2),
        actual_depart_time=now - timedelta(hours=1),
    )
    db_session.add(trip)
    db_session.commit()
    db_session.refresh(trip)

    # Login as DSP
    client.post("/api/v1/auth/login", json={"username": "dsp_test", "password": "password123"})

    # Report delivery failure
    fail_res = client.post(
        f"/api/v1/trips/{trip.id}/deliver",
        data={
            "actual_delivery_time": now.isoformat(),
            "result": "FAILED",
            "delivery_notes": "Khách từ chối nhận do kiện hàng bị ngấm nước",
        },
    )
    assert fail_res.status_code == 200
    db_session.refresh(trip)
    assert trip.status == TripStatus.IN_TRANSIT.value

    # Attempting to complete must fail
    comp_res = client.post(
        f"/api/v1/trips/{trip.id}/complete",
        json={"actual_completed_time": now.isoformat()},
    )
    assert comp_res.status_code == 400


def test_delivery_rbac_permissions(client: TestClient, db_session, seed_test_users):
    truck = Truck(
        plate_number="51C-RBAC.01",
        normalized_plate="51CRBAC01",
        truck_type="Tải 5T",
        capacity_kg=5000,
        status=TruckStatus.ACTIVE.value,
    )
    driver = Driver(
        driver_code="DRV_RBAC01",
        full_name="Tài Xế RBAC",
        phone_number="0911444333",
        status=DriverStatus.ACTIVE.value,
    )
    db_session.add_all([truck, driver])
    db_session.commit()
    db_session.refresh(truck)
    db_session.refresh(driver)

    now = datetime.now()
    trip = Trip(
        reference_code="TRIP-RBAC-01",
        sender_name="Kho RBAC",
        sender_phone="0911555666",
        pickup_address="Kho 1",
        delivery_address="Kho 2",
        cargo_type="Hàng mẫu",
        cargo_weight_kg=1000,
        status=TripStatus.IN_TRANSIT.value,
        assigned_truck_id=truck.id,
        assigned_driver_id=driver.id,
        actual_pickup_time=now - timedelta(hours=2),
        actual_depart_time=now - timedelta(hours=1),
    )
    db_session.add(trip)
    db_session.commit()
    db_session.refresh(trip)

    # 1. Login as SAL
    client.post("/api/v1/auth/login", json={"username": "sal_test", "password": "password123"})

    # Try deliver -> 403 Forbidden
    files = [("evidence_files", ("pod.pdf", io.BytesIO(b"data"), "application/pdf"))]
    deliv_res = client.post(
        f"/api/v1/trips/{trip.id}/deliver",
        data={"actual_delivery_time": now.isoformat(), "result": "SUCCESS", "recipient_name": "Test"},
        files=files,
    )
    assert deliv_res.status_code == 403

    # Try complete -> 403 Forbidden
    comp_res = client.post(
        f"/api/v1/trips/{trip.id}/complete",
        json={"actual_completed_time": now.isoformat()},
    )
    assert comp_res.status_code == 403

    # But SAL can read evidence
    evidence_res = client.get(f"/api/v1/trips/{trip.id}/evidence")
    assert evidence_res.status_code == 200
