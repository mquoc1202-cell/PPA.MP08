import io
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.trip import Trip, TripStatus
from src.models.trip_issue import TripIssue, IssueStatus
from src.models.booking import ResourceBooking, ResourceType, BookingStatus, ServiceType
from src.models.trip_event import TripEvent, TripEventType
from src.repositories.trip_repo import TripRepository
from src.services.delivery_service import DeliveryService, UploadedEvidenceFile


def login_client(client: TestClient, username: str = "dsp_test", password: str = "password123"):
    """Helper to authenticate and store session cookies in client."""
    client.cookies.clear()
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200


def seed_base_trip(db: Session, ref_suffix: str = "01", status: str = TripStatus.IN_TRANSIT.value) -> tuple[Truck, Driver, Trip]:
    """Helper to create truck, driver, and trip in DB."""
    now = datetime.now(timezone.utc)
    truck = Truck(
        plate_number=f"29C-{ref_suffix}.99",
        normalized_plate=f"29C{ref_suffix}99",
        truck_type="Tải thùng 5T",
        capacity_kg=5000,
        status=TruckStatus.ACTIVE.value,
    )
    driver = Driver(
        driver_code=f"DRV_{ref_suffix}",
        full_name=f"Tài Xế {ref_suffix}",
        phone_number="0988776655",
        status=DriverStatus.ACTIVE.value,
    )
    db.add_all([truck, driver])
    db.commit()
    db.refresh(truck)
    db.refresh(driver)

    trip = Trip(
        reference_code=f"TRIP-INC-{ref_suffix}",
        sender_name="Cong ty TNHH Vận Tải Test",
        sender_phone="0912345678",
        pickup_address="Kho A - Ha Noi",
        delivery_address="Kho B - Da Nang",
        cargo_type="Hang tieu dung",
        cargo_weight_kg=3500,
        status=status,
        assigned_truck_id=truck.id,
        assigned_driver_id=driver.id,
        estimated_start_time=now - timedelta(hours=4),
        estimated_end_time=now + timedelta(hours=4),
        actual_pickup_time=now - timedelta(hours=4),
        actual_depart_time=now - timedelta(hours=3),
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)

    booking_truck = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code=trip.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=trip.estimated_start_time,
        end_time=trip.estimated_end_time,
        status=BookingStatus.IN_PROGRESS.value,
    )
    booking_driver = ResourceBooking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver.id,
        reference_code=trip.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=trip.estimated_start_time,
        end_time=trip.estimated_end_time,
        status=BookingStatus.IN_PROGRESS.value,
    )
    db.add_all([booking_truck, booking_driver])
    db.commit()

    return truck, driver, trip


def test_overdue_delay_flag_and_disappearance_on_delivery(client: TestClient, db_session: Session, seed_test_users):
    """
    US2 Integration Test:
    - Trip past estimated_end_time shows as delayed (is_delayed == True).
    - Web view displays overdue warning banner and overdue tab shows the trip.
    - Once delivered (status -> DELIVERED), overdue flag disappears immediately even if time is past.
    """
    login_client(client, "dsp_test", "password123")
    truck, driver, trip = seed_base_trip(db_session, "DLY01")

    # Set estimated_end_time to 2 hours ago -> overdue!
    now = datetime.now(timezone.utc)
    trip.estimated_end_time = now - timedelta(hours=2)
    db_session.commit()
    db_session.refresh(trip)

    # 1. Verify property logic
    assert trip.is_delayed is True

    # 2. Check web detail view contains warning banner
    res_web = client.get(f"/trips/{trip.id}")
    assert res_web.status_code == 200
    assert "QUÁ HẠN VẬN HÀNH" in res_web.text

    # 3. Check web list view filter_mode=delayed contains trip
    res_list = client.get("/trips?filter_mode=delayed")
    assert res_list.status_code == 200
    assert trip.reference_code in res_list.text

    # 4. Confirm delivery with POD
    delivery_service = DeliveryService(db_session)
    pdf_content = b"%PDF-1.4 Mock POD File Content"
    mock_file = UploadedEvidenceFile(
        filename="pod_delivery_dly.pdf",
        content=pdf_content,
        content_type="application/pdf",
        evidence_type="POD",
    )
    from src.schemas.trip import RecordDeliveryRequest
    deliv_req = RecordDeliveryRequest(
        actual_delivery_time=now - timedelta(minutes=10),
        recipient_name="Nguyen Van Nhan",
        result="SUCCESS",
        delivery_notes="Giao thanh cong du tre gio",
    )
    updated_trip = delivery_service.record_delivery(trip.id, deliv_req, files=[mock_file], user_id=1)

    assert updated_trip.status == TripStatus.DELIVERED.value
    # Overdue flag MUST disappear when delivered!
    assert updated_trip.is_delayed is False

    # 5. Check detail view no longer shows overdue banner
    res_web_after = client.get(f"/trips/{trip.id}")
    assert res_web_after.status_code == 200
    assert "QUÁ HẠN VẬN HÀNH" not in res_web_after.text


def test_incident_audit_timeline_ordering(client: TestClient, db_session: Session, seed_test_users):
    """
    US4 Integration Test:
    - Log issue -> ISSUE_LOGGED event
    - Reschedule trip -> SCHEDULE_DELAYED event
    - Resolve issue -> ISSUE_RESOLVED event
    - Verify timeline sequence and HTML rendering
    """
    login_client(client, "dsp_test", "password123")
    truck, driver, trip = seed_base_trip(db_session, "AUD01")

    now = datetime.now(timezone.utc)

    # 1. Log Issue
    issue_payload = {
        "issue_type": "TRAFFIC_JAM",
        "description": "Ùn tắc nghiêm trọng tại đèo Hải Vân do sạt lở",
        "occurred_at": (now - timedelta(hours=1)).isoformat(),
        "handled_by": "CSGT Da Nang",
        "estimated_resolution_time": (now + timedelta(hours=3)).isoformat(),
    }
    res_log = client.post(f"/api/v1/trips/{trip.id}/issues", json=issue_payload)
    assert res_log.status_code == 201
    issue_id = res_log.json()["data"]["id"]

    # 2. Reschedule Trip
    new_end_time = trip.estimated_end_time + timedelta(hours=3)
    res_sched = client.post(
        f"/api/v1/trips/{trip.id}/reschedule",
        json={"new_estimated_end_time": new_end_time.isoformat(), "reason": "Chờ thông đường đèo Hải Vân"},
    )
    assert res_sched.status_code == 200

    # 3. Resolve Issue
    resolve_payload = {
        "resolution_notes": "Đã thông tuyến 1 làn xe, xe đã tiếp tục di chuyển"
    }
    res_resolve = client.post(
        f"/api/v1/trips/{trip.id}/issues/{issue_id}/resolve",
        json=resolve_payload,
    )
    assert res_resolve.status_code == 200

    # 4. Check audit timeline events
    res_events = client.get(f"/api/v1/trips/{trip.id}/events")
    assert res_events.status_code == 200
    events = res_events.json()["data"]
    event_types = [e["event_type"] for e in events]

    assert TripEventType.ISSUE_LOGGED.value in event_types
    assert TripEventType.SCHEDULE_DELAYED.value in event_types
    assert TripEventType.ISSUE_RESOLVED.value in event_types

    # Find indexes to confirm chronological ordering
    idx_logged = event_types.index(TripEventType.ISSUE_LOGGED.value)
    idx_delayed = event_types.index(TripEventType.SCHEDULE_DELAYED.value)
    idx_resolved = event_types.index(TripEventType.ISSUE_RESOLVED.value)
    assert idx_logged < idx_delayed < idx_resolved

    # 5. Check detail page displays the incident log and timeline elements
    res_detail = client.get(f"/trips/{trip.id}")
    assert res_detail.status_code == 200
    assert "Nhật Ký Sự Cố Chuyến Hàng" in res_detail.text
    assert "TRAFFIC_JAM" in res_detail.text
    assert "Ùn tắc nghiêm trọng tại đèo Hải Vân" in res_detail.text
    assert "Đã thông tuyến 1 làn xe" in res_detail.text


def test_rbac_protection_for_incidents_and_rescheduling(client: TestClient, db_session: Session, seed_test_users):
    """
    US5 RBAC Test:
    - DSP can log issues, resolve issues, reschedule.
    - SAL and MGR are rejected with HTTP 403 Forbidden for mutation endpoints.
    - SAL and MGR can view trip details (read-only).
    - Web UI hides action buttons for SAL and MGR.
    """
    truck, driver, trip = seed_base_trip(db_session, "RBAC01")

    # 1. As DSP: create an issue first
    login_client(client, "dsp_test", "password123")
    res_dsp = client.post(
        f"/api/v1/trips/{trip.id}/issues",
        json={
            "issue_type": "VEHICLE_BREAKDOWN",
            "description": "Lủng lốp xe trên cao tốc",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res_dsp.status_code == 201
    issue_id = res_dsp.json()["data"]["id"]

    # 2. Test as SAL (Sales): Must get 403 Forbidden on writes
    login_client(client, "sal_test", "password123")

    # SAL cannot create issue
    res_sal_create = client.post(
        f"/api/v1/trips/{trip.id}/issues",
        json={"issue_type": "OTHER", "description": "SAL thử tạo sự cố"},
    )
    assert res_sal_create.status_code == 403

    # SAL cannot resolve issue
    res_sal_resolve = client.post(
        f"/api/v1/trips/{trip.id}/issues/{issue_id}/resolve",
        json={"resolution_notes": "SAL thử đóng sự cố"},
    )
    assert res_sal_resolve.status_code == 403

    # SAL cannot reschedule
    res_sal_sched = client.post(
        f"/api/v1/trips/{trip.id}/reschedule",
        json={
            "new_estimated_end_time": (trip.estimated_end_time + timedelta(hours=2)).isoformat(),
            "reason": "SAL lùi lịch",
        },
    )
    assert res_sal_sched.status_code == 403

    # SAL CAN view trip details (read-only)
    res_sal_view = client.get(f"/trips/{trip.id}")
    assert res_sal_view.status_code == 200
    # Buttons should NOT be present for SAL
    assert "onclick=\"showCreateIssueModal()\"" not in res_sal_view.text
    assert "onclick=\"showRescheduleModal()\"" not in res_sal_view.text

    # 3. Test as MGR (Manager): Must get 403 Forbidden on writes
    login_client(client, "mgr_test", "password123")

    res_mgr_create = client.post(
        f"/api/v1/trips/{trip.id}/issues",
        json={"issue_type": "OTHER", "description": "MGR thử tạo sự cố"},
    )
    assert res_mgr_create.status_code == 403

    res_mgr_sched = client.post(
        f"/api/v1/trips/{trip.id}/reschedule",
        json={
            "new_estimated_end_time": (trip.estimated_end_time + timedelta(hours=2)).isoformat(),
            "reason": "MGR lùi lịch",
        },
    )
    assert res_mgr_sched.status_code == 403


def test_incident_and_delay_repository_filtering(db_session: Session):
    """
    US5 Repository Test:
    - Test filter_trips with has_issues=True and is_delayed=True.
    - Test count_delayed_trips() and count_trips_with_open_issues().
    """
    now = datetime.now(timezone.utc)
    truck_a, driver_a, trip_with_issue = seed_base_trip(db_session, "FLT_ISS")
    truck_b, driver_b, trip_delayed = seed_base_trip(db_session, "FLT_DLY")
    truck_c, driver_c, trip_normal = seed_base_trip(db_session, "FLT_NORM")

    # Add open issue to trip_with_issue
    issue = TripIssue(
        trip_id=trip_with_issue.id,
        issue_type="VEHICLE_BREAKDOWN",
        description="Hong may",
        status=IssueStatus.OPEN.value,
        occurred_at=now,
    )
    db_session.add(issue)

    # Set trip_delayed to overdue
    trip_delayed.estimated_end_time = now - timedelta(hours=5)

    db_session.commit()

    repo = TripRepository(db_session)

    # 1. Filter has_issues=True
    issues_trips, issues_count = repo.filter_trips(has_issues=True)
    assert any(t.id == trip_with_issue.id for t in issues_trips)
    assert all(t.has_open_issues for t in issues_trips)

    # 2. Filter is_delayed=True
    delayed_trips, delayed_count = repo.filter_trips(is_delayed=True)
    assert any(t.id == trip_delayed.id for t in delayed_trips)
    assert all(t.is_delayed for t in delayed_trips)

    # 3. Counts
    total_delayed = repo.count_delayed_trips()
    assert total_delayed >= 1
    total_issues = repo.count_trips_with_open_issues()
    assert total_issues >= 1
