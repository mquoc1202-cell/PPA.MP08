import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.trip import Trip, TripStatus
from src.models.trip_event import TripEvent, TripEventType
from src.models.trip_evidence import TripEvidence
from src.models.trip_issue import TripIssue, IssueStatus
from src.models.booking import ResourceBooking, ResourceType, BookingStatus, ServiceType
from src.schemas.trip import RecordDeliveryRequest, CompleteTripRequest
from src.services.delivery_service import DeliveryService, UploadedEvidenceFile
from src.core.exceptions import BusinessRuleViolationError, EntityNotFoundError


def _setup_transit_fixtures(db: Session) -> Trip:
    """Setup a trip in IN_TRANSIT status with truck and driver bookings."""
    truck = Truck(
        plate_number="51C-DELIV.01",
        normalized_plate="51CDELIV01",
        truck_type="Tải nặng 8T",
        capacity_kg=8000,
        status=TruckStatus.ACTIVE.value,
    )
    driver = Driver(
        driver_code="DRV_DL01",
        full_name="Nguyễn Văn Tài Xế Giao Hàng",
        phone_number="0911888999",
        status=DriverStatus.ACTIVE.value,
    )
    db.add_all([truck, driver])
    db.commit()
    db.refresh(truck)
    db.refresh(driver)

    now = datetime.now()
    trip = Trip(
        reference_code="TRIP-TEST-DELIV-01",
        sender_name="Công ty Hóa Chất Miền Nam",
        sender_phone="0909888777",
        pickup_address="Kho Hóa Chất, KCN Hiệp Phước, TP.HCM",
        delivery_address="Nhà máy Sản xuất Phân bón, KCN Long Thành, Đồng Nai",
        cargo_type="Hóa chất công nghiệp đóng can",
        cargo_weight_kg=6000,
        status=TripStatus.IN_TRANSIT.value,
        assigned_truck_id=truck.id,
        assigned_driver_id=driver.id,
        actual_pickup_time=now - timedelta(hours=4),
        actual_depart_time=now - timedelta(hours=3),
        pickup_recorded_at=now - timedelta(hours=4),
        depart_recorded_at=now - timedelta(hours=3),
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)

    # Bookings in IN_PROGRESS state
    b_truck = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck.id,
        reference_code=trip.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=now - timedelta(hours=4),
        end_time=now + timedelta(hours=4),
        status=BookingStatus.IN_PROGRESS.value,
    )
    b_driver = ResourceBooking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver.id,
        reference_code=trip.reference_code,
        service_type=ServiceType.FREIGHT.value,
        start_time=now - timedelta(hours=4),
        end_time=now + timedelta(hours=4),
        status=BookingStatus.IN_PROGRESS.value,
    )
    db.add_all([b_truck, b_driver])
    db.commit()
    return trip


def test_record_delivery_success(db_session: Session):
    trip = _setup_transit_fixtures(db_session)
    service = DeliveryService(db_session)

    deliv_time = datetime.now() - timedelta(minutes=30)
    req = RecordDeliveryRequest(
        actual_delivery_time=deliv_time,
        recipient_name="Trần Thị Thu Nhận Hàng",
        result="SUCCESS",
        delivery_notes="Giao đủ 100 can hóa chất nguyên niêm phong",
    )
    evidence_files = [
        UploadedEvidenceFile(
            filename="bien_ban_ban_giao.pdf",
            content=b"%PDF-1.4 sample content...",
            content_type="application/pdf",
        )
    ]

    result = service.record_delivery(trip_id=trip.id, req=req, files=evidence_files, user_id=1)

    assert result.status == TripStatus.DELIVERED.value
    assert result.recipient_name == "Trần Thị Thu Nhận Hàng"
    assert result.actual_delivery_time is not None
    assert result.delivery_recorded_at is not None

    # Verify TripEvidence created
    evidences = db_session.query(TripEvidence).filter(TripEvidence.trip_id == trip.id).all()
    assert len(evidences) == 1
    assert evidences[0].file_name == "bien_ban_ban_giao.pdf"
    assert evidences[0].mime_type == "application/pdf"
    assert evidences[0].evidence_type == "POD"

    # Verify TripEvent created
    events = db_session.query(TripEvent).filter(TripEvent.trip_id == trip.id).all()
    event_types = [e.event_type for e in events]
    assert TripEventType.DELIVERY_CONFIRMED.value in event_types


def test_record_delivery_invalid_state_rejection(db_session: Session):
    trip = _setup_transit_fixtures(db_session)
    trip.status = TripStatus.PICKED_UP.value
    db_session.commit()

    service = DeliveryService(db_session)
    req = RecordDeliveryRequest(
        actual_delivery_time=datetime.now(),
        recipient_name="Trần Thị Thu",
        result="SUCCESS",
    )
    evidence_files = [
        UploadedEvidenceFile(
            filename="pod.jpg",
            content=b"\xff\xd8\xff\xe0 sample jpeg",
            content_type="image/jpeg",
        )
    ]

    with pytest.raises(BusinessRuleViolationError) as exc_info:
        service.record_delivery(trip_id=trip.id, req=req, files=evidence_files, user_id=1)
    assert "IN_TRANSIT" in str(exc_info.value)


def test_record_delivery_missing_pod_rejection(db_session: Session):
    trip = _setup_transit_fixtures(db_session)
    service = DeliveryService(db_session)

    req = RecordDeliveryRequest(
        actual_delivery_time=datetime.now(),
        recipient_name="Trần Thị Thu",
        result="SUCCESS",
    )

    with pytest.raises(BusinessRuleViolationError) as exc_info:
        service.record_delivery(trip_id=trip.id, req=req, files=[], user_id=1)
    assert "bằng chứng" in str(exc_info.value).lower() or "pod" in str(exc_info.value).lower()


def test_record_delivery_time_before_pickup_rejection(db_session: Session):
    trip = _setup_transit_fixtures(db_session)
    service = DeliveryService(db_session)

    # Pickup was 4 hours ago, attempt delivery 5 hours ago
    invalid_deliv_time = datetime.now() - timedelta(hours=5)
    req = RecordDeliveryRequest(
        actual_delivery_time=invalid_deliv_time,
        recipient_name="Trần Thị Thu",
        result="SUCCESS",
    )
    evidence_files = [
        UploadedEvidenceFile(
            filename="pod.png",
            content=b"\x89PNG\r\n sample png",
            content_type="image/png",
        )
    ]

    with pytest.raises(BusinessRuleViolationError) as exc_info:
        service.record_delivery(trip_id=trip.id, req=req, files=evidence_files, user_id=1)
    assert "nhận hàng" in str(exc_info.value).lower()


def test_record_delivery_failure_flow(db_session: Session):
    trip = _setup_transit_fixtures(db_session)
    service = DeliveryService(db_session)

    deliv_time = datetime.now() - timedelta(minutes=20)
    req = RecordDeliveryRequest(
        actual_delivery_time=deliv_time,
        recipient_name=None,
        result="FAILED",
        delivery_notes="Kho đích đóng cửa nghỉ lễ đột xuất, không có người tiếp nhận",
    )

    result = service.record_delivery(trip_id=trip.id, req=req, files=[], user_id=1)

    # Status must remain IN_TRANSIT
    assert result.status == TripStatus.IN_TRANSIT.value

    # TripIssue must be logged
    issues = db_session.query(TripIssue).filter(TripIssue.trip_id == trip.id).all()
    assert len(issues) == 1
    assert issues[0].status == IssueStatus.OPEN.value
    assert "Kho đích đóng cửa" in issues[0].description

    # Event logged
    events = db_session.query(TripEvent).filter(TripEvent.trip_id == trip.id).all()
    event_types = [e.event_type for e in events]
    assert TripEventType.DELIVERY_FAILED.value in event_types


def test_complete_trip_success(db_session: Session):
    trip = _setup_transit_fixtures(db_session)
    service = DeliveryService(db_session)

    # First deliver successfully
    deliv_time = datetime.now() - timedelta(hours=1)
    service.record_delivery(
        trip_id=trip.id,
        req=RecordDeliveryRequest(
            actual_delivery_time=deliv_time,
            recipient_name="Người Nhận Hoàn Tất",
            result="SUCCESS",
        ),
        files=[
            UploadedEvidenceFile(
                filename="pod_final.pdf",
                content=b"%PDF-1.4 final evidence",
                content_type="application/pdf",
            )
        ],
        user_id=1,
    )

    # Now complete trip
    completed_time = datetime.now() - timedelta(minutes=15)
    result = service.complete_trip(
        trip_id=trip.id,
        req=CompleteTripRequest(
            actual_completed_time=completed_time,
            notes="Kết thúc chuyến thành công, xe và tài xế giải phóng",
        ),
        user_id=1,
    )

    assert result.status == TripStatus.COMPLETED.value
    assert result.actual_completed_time is not None
    assert result.completed_recorded_at is not None

    # Verify bookings transitioned to COMPLETED
    bookings = db_session.query(ResourceBooking).filter(ResourceBooking.reference_code == trip.reference_code).all()
    assert len(bookings) == 2
    for b in bookings:
        assert b.status == BookingStatus.COMPLETED.value

    # Verify event logged
    events = db_session.query(TripEvent).filter(TripEvent.trip_id == trip.id).all()
    event_types = [e.event_type for e in events]
    assert TripEventType.TRIP_COMPLETED.value in event_types


def test_complete_trip_not_delivered_rejection(db_session: Session):
    trip = _setup_transit_fixtures(db_session)
    service = DeliveryService(db_session)

    with pytest.raises(BusinessRuleViolationError) as exc_info:
        service.complete_trip(
            trip_id=trip.id,
            req=CompleteTripRequest(actual_completed_time=datetime.now()),
            user_id=1,
        )
    assert "DELIVERED" in str(exc_info.value)


def test_complete_trip_future_time_rejection(db_session: Session):
    trip = _setup_transit_fixtures(db_session)
    service = DeliveryService(db_session)

    # Deliver first
    service.record_delivery(
        trip_id=trip.id,
        req=RecordDeliveryRequest(
            actual_delivery_time=datetime.now() - timedelta(hours=1),
            recipient_name="Người Nhận",
            result="SUCCESS",
        ),
        files=[
            UploadedEvidenceFile(
                filename="pod.jpg",
                content=b"sample",
                content_type="image/jpeg",
            )
        ],
        user_id=1,
    )

    # Attempt to complete with future time (e.g. tomorrow)
    future_time = datetime.now() + timedelta(days=1)
    with pytest.raises(BusinessRuleViolationError) as exc_info:
        service.complete_trip(
            trip_id=trip.id,
            req=CompleteTripRequest(actual_completed_time=future_time),
            user_id=1,
        )
    assert "tương lai" in str(exc_info.value).lower()
