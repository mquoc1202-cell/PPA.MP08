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
from src.core.exceptions import ScheduleConflictError, BusinessRuleViolationError


def _setup_transitions_fixtures(db: Session):
    truck = Truck(
        plate_number="51C-TRANS.01",
        normalized_plate="51CTRANS01",
        truck_type="Tải trung 8T",
        capacity_kg=8000,
        status=TruckStatus.ACTIVE.value,
    )
    driver = Driver(
        driver_code="DRV_TR01",
        full_name="Driver Transition One",
        phone_number="0911888999",
        status=DriverStatus.ACTIVE.value,
    )
    db.add_all([truck, driver])
    db.commit()
    db.refresh(truck)
    db.refresh(driver)

    now = datetime.now()
    trip1 = Trip(
        reference_code="TRIP-TRANS-01",
        sender_name="Sender One",
        sender_phone="0901111222",
        pickup_address="Kho 1",
        delivery_address="Kho 2",
        cargo_type="Hàng gia dụng",
        cargo_weight_kg=4000,
        status=TripStatus.ASSIGNED.value,
        assigned_truck_id=truck.id,
        assigned_driver_id=driver.id,
        estimated_start_time=now,
        estimated_end_time=now + timedelta(hours=6),
    )
    trip2 = Trip(
        reference_code="TRIP-TRANS-02",
        sender_name="Sender Two",
        sender_phone="0903333444",
        pickup_address="Kho 3",
        delivery_address="Kho 4",
        cargo_type="Hàng may mặc",
        cargo_weight_kg=3500,
        status=TripStatus.ASSIGNED.value,
        assigned_truck_id=truck.id,
        assigned_driver_id=driver.id,
        estimated_start_time=now + timedelta(hours=8),
        estimated_end_time=now + timedelta(hours=14),
    )
    db.add_all([trip1, trip2])
    db.commit()

    # Trip1 confirmed bookings
    b1_truck = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code=trip1.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=now,
        end_time=now + timedelta(hours=6),
        status=BookingStatus.CONFIRMED.value,
    )
    b1_driver = ResourceBooking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver.id,
        reference_code=trip1.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=now,
        end_time=now + timedelta(hours=6),
        status=BookingStatus.CONFIRMED.value,
    )
    # Trip2 confirmed bookings
    b2_truck = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code=trip2.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=now + timedelta(hours=8),
        end_time=now + timedelta(hours=14),
        status=BookingStatus.CONFIRMED.value,
    )
    b2_driver = ResourceBooking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver.id,
        reference_code=trip2.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=now + timedelta(hours=8),
        end_time=now + timedelta(hours=14),
        status=BookingStatus.CONFIRMED.value,
    )
    db.add_all([b1_truck, b1_driver, b2_truck, b2_driver])
    db.commit()

    return truck, driver, trip1, trip2


def test_br09_busy_resource_rejection(db_session: Session):
    """
    US3 (BR-09): When truck/driver is actively IN_PROGRESS on trip1,
    trip2 cannot record pickup until trip1 is completed.
    """
    truck, driver, trip1, trip2 = _setup_transitions_fixtures(db_session)
    service = TripTrackingService(db_session)

    # 1. Trip1 records pickup -> enters PICKED_UP and bookings become IN_PROGRESS
    service.record_pickup(trip1.id, RecordPickupRequest(
        actual_pickup_time=datetime(2026, 12, 1, 8, 0),
        handover_person="Kho 1 Trưởng",
        actual_cargo_weight_kg=4000,
    ))
    db_session.refresh(trip1)
    assert trip1.status == TripStatus.PICKED_UP.value

    # 2. Trip2 attempts pickup with same truck and driver -> Must be rejected per BR-09
    with pytest.raises(ScheduleConflictError) as exc_info:
        service.record_pickup(trip2.id, RecordPickupRequest(
            actual_pickup_time=datetime(2026, 12, 1, 9, 0),
            handover_person="Kho 2 Trưởng",
            actual_cargo_weight_kg=3500,
        ))

    assert "BR-09" in str(exc_info.value) or "chưa hoàn tất" in str(exc_info.value)
    db_session.refresh(trip2)
    assert trip2.status == TripStatus.ASSIGNED.value


def test_departure_and_timeline_lifecycle(db_session: Session):
    """
    US4: Transition from PICKED_UP to IN_TRANSIT with actual departure time.
    US5: Verifies audit timeline events for both pickup and departure.
    """
    truck, driver, trip1, _ = _setup_transitions_fixtures(db_session)
    service = TripTrackingService(db_session)

    pickup_time = datetime(2026, 12, 1, 8, 0)
    service.record_pickup(trip1.id, RecordPickupRequest(
        actual_pickup_time=pickup_time,
        handover_person="Thủ kho A",
        actual_cargo_weight_kg=4000,
    ), user_id=1)

    # 1. Reject departure before pickup time
    with pytest.raises(BusinessRuleViolationError) as exc_info:
        service.record_departure(trip1.id, RecordDepartureRequest(
            actual_depart_time=datetime(2026, 12, 1, 7, 30),
        ))
    assert "trước thời điểm nhận hàng" in str(exc_info.value)

    # 2. Valid departure
    depart_time = datetime(2026, 12, 1, 8, 45)
    updated_trip = service.record_departure(trip1.id, RecordDepartureRequest(
        actual_depart_time=depart_time,
        notes="Xe đã xuất phát đi đường quốc lộ",
    ), user_id=1)

    assert updated_trip.status == TripStatus.IN_TRANSIT.value
    assert updated_trip.actual_depart_time == depart_time
    assert updated_trip.depart_recorded_at is not None

    # 3. Check Timeline Events
    events = db_session.query(TripEvent).filter(TripEvent.trip_id == trip1.id).order_by(TripEvent.actual_time.asc()).all()
    assert len(events) == 2
    assert events[0].event_type == TripEventType.PICKUP_CONFIRMED.value
    assert events[0].from_status == "ASSIGNED"
    assert events[0].to_status == "PICKED_UP"

    assert events[1].event_type == TripEventType.DEPARTURE_CONFIRMED.value
    assert events[1].from_status == "PICKED_UP"
    assert events[1].to_status == "IN_TRANSIT"


def test_api_departure_and_rbac(client: TestClient, db_session: Session, seed_test_users):
    """
    Verify RBAC on departure and events API endpoints.
    """
    truck, driver, trip1, _ = _setup_transitions_fixtures(db_session)
    service = TripTrackingService(db_session)

    # Advance trip1 to PICKED_UP
    service.record_pickup(trip1.id, RecordPickupRequest(
        actual_pickup_time=datetime(2026, 12, 1, 8, 0),
        handover_person="Thủ kho A",
        actual_cargo_weight_kg=4000,
    ))

    # 1. Unauthenticated -> 401
    resp_unauth = client.post(f"/api/v1/trips/{trip1.id}/depart", json={"actual_depart_time": "2026-12-01T08:30:00"})
    assert resp_unauth.status_code == 401

    # 2. SAL role -> 403 Forbidden for POST /depart
    client.post("/api/v1/auth/login", json={"username": "sal_test", "password": "password123"})
    resp_sal = client.post(f"/api/v1/trips/{trip1.id}/depart", json={"actual_depart_time": "2026-12-01T08:30:00"})
    assert resp_sal.status_code == 403

    # SAL can read timeline events -> 200 OK
    resp_sal_events = client.get(f"/api/v1/trips/{trip1.id}/events")
    assert resp_sal_events.status_code == 200
    assert len(resp_sal_events.json()["data"]) == 1
    client.post("/api/v1/auth/logout")

    # 3. DSP role -> 200 OK
    client.post("/api/v1/auth/login", json={"username": "dsp_test", "password": "password123"})
    resp_dsp = client.post(f"/api/v1/trips/{trip1.id}/depart", json={"actual_depart_time": "2026-12-01T08:30:00"})
    assert resp_dsp.status_code == 200
    assert resp_dsp.json()["data"]["status"] == "IN_TRANSIT"


def test_trip_web_create_flow(client: TestClient, seed_test_users, db_session: Session):
    """Test Web UI GET and POST /trips/create."""
    # 1. Login as DSP
    login_resp = client.post("/login", data={"username": "dsp_test", "password": "password123"}, follow_redirects=False)
    assert login_resp.status_code == 303

    # 2. GET /trips/create -> 200 OK
    res_get = client.get("/trips/create")
    assert res_get.status_code == 200
    assert "TẠO MỚI ĐƠN HÀNG" in res_get.text

    # 3. POST /trips/create with invalid weight -> 400 Bad Request
    res_invalid = client.post("/trips/create", data={
        "sender_name": "Công ty Test",
        "sender_phone": "0911222333",
        "pickup_address": "Kho A",
        "delivery_address": "Kho B",
        "cargo_weight_kg": 0,
        "cargo_type": "Hàng nhẹ",
    })
    assert res_invalid.status_code == 400
    assert "Khối lượng hàng hóa phải lớn hơn 0 kg" in res_invalid.text

    # 4. POST /trips/create valid -> 303 Redirect to /trips?success=created
    res_valid = client.post("/trips/create", data={
        "sender_name": "Công ty Sản Xuất Á Châu",
        "sender_phone": "0988776655",
        "pickup_address": "Kho Tổng Sóng Thần",
        "delivery_address": "Cảng Cát Lái",
        "cargo_weight_kg": 4200,
        "cargo_type": "Hàng dệt may",
        "notes": "Hàng xuất khẩu đóng container",
    }, follow_redirects=False)

    assert res_valid.status_code == 303
    assert "/trips?success=created" in res_valid.headers["location"]

    # Verify created in DB
    created_trip = db_session.query(Trip).filter(Trip.sender_name == "Công ty Sản Xuất Á Châu").first()
    assert created_trip is not None
    assert created_trip.status == TripStatus.UNASSIGNED.value
    assert created_trip.cargo_weight_kg == 4200
    assert created_trip.reference_code.startswith("TRIP-")

