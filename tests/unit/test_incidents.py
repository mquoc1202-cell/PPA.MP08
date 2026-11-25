from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session
from src.models.trip import Trip, TripStatus
from src.models.trip_issue import TripIssue, IssueStatus
from src.models.trip_event import TripEvent, TripEventType
from src.schemas.trip import CreateTripIssueRequest, ResolveTripIssueRequest
from src.services.incident_service import IncidentService
from src.core.exceptions import BusinessRuleException, NotFoundException


def create_test_trip(db: Session, status: str = TripStatus.IN_TRANSIT.value) -> Trip:
    """Helper to create an active trip for testing."""
    now = datetime.now(timezone.utc)
    trip = Trip(
        reference_code=f"TRIP-TEST-{now.timestamp()}",
        sender_name="Cong ty TNHH Thuong Mai Test",
        sender_phone="0912345678",
        pickup_address="Kho A, Ha Noi",
        delivery_address="Kho B, Hai Phong",
        cargo_weight_kg=3500,
        cargo_type="May moc co khi",
        status=status,
        estimated_start_time=now - timedelta(hours=3),
        estimated_end_time=now + timedelta(hours=3),
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


def test_log_issue_success(db_session: Session):
    """Test DSP successfully logs a new incident with OPEN status and audit event."""
    service = IncidentService(db_session)
    trip = create_test_trip(db_session)

    req = CreateTripIssueRequest(
        issue_type="VEHICLE_BREAKDOWN",
        description="Xe bi no lop tren cao toc Phap Van",
        occurred_at=datetime.now(timezone.utc),
        handled_by="Tai xe Nguyen Van A & Cuu ho cao toc",
        estimated_resolution_time=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    issue = service.log_issue(trip.id, req, user_id=1)

    assert issue.id is not None
    assert issue.trip_id == trip.id
    assert issue.issue_type == "VEHICLE_BREAKDOWN"
    assert issue.description == "Xe bi no lop tren cao toc Phap Van"
    assert issue.status == IssueStatus.OPEN.value
    assert issue.handled_by == "Tai xe Nguyen Van A & Cuu ho cao toc"
    assert issue.reported_by_user_id == 1

    # Verify TripEvent audit trail
    event = (
        db_session.query(TripEvent)
        .filter(TripEvent.trip_id == trip.id, TripEvent.event_type == TripEventType.ISSUE_LOGGED.value)
        .first()
    )
    assert event is not None
    assert event.from_status == trip.status
    assert event.to_status == trip.status


def test_log_issue_nonexistent_trip_raises_not_found(db_session: Session):
    """Test logging an issue for non-existent trip raises NotFoundException."""
    service = IncidentService(db_session)
    req = CreateTripIssueRequest(
        issue_type="OTHER",
        description="Su co bat thuong",
    )
    with pytest.raises(NotFoundException):
        service.log_issue(999999, req, user_id=1)


def test_resolve_issue_success(db_session: Session):
    """Test successfully resolving an issue with resolution notes."""
    service = IncidentService(db_session)
    trip = create_test_trip(db_session)

    log_req = CreateTripIssueRequest(
        issue_type="TRAFFIC_CONGESTION",
        description="Kẹt xe cầu Thanh Trì nghiêm trọng",
    )
    issue = service.log_issue(trip.id, log_req, user_id=1)

    resolve_req = ResolveTripIssueRequest(
        resolution_notes="Giao thông đã thông thoáng sau 45 phút, xe đã qua cầu an toàn."
    )
    resolved = service.resolve_issue(trip.id, issue.id, resolve_req, user_id=1)

    assert resolved.status == IssueStatus.RESOLVED.value
    assert resolved.resolution_notes == "Giao thông đã thông thoáng sau 45 phút, xe đã qua cầu an toàn."
    assert resolved.resolved_at is not None

    # Verify TripEvent audit trail
    event = (
        db_session.query(TripEvent)
        .filter(TripEvent.trip_id == trip.id, TripEvent.event_type == TripEventType.ISSUE_RESOLVED.value)
        .first()
    )
    assert event is not None


def test_resolve_issue_missing_notes_rejection(db_session: Session):
    """Test resolving an issue with blank resolution notes raises validation error or BusinessRuleException."""
    import pydantic
    service = IncidentService(db_session)
    trip = create_test_trip(db_session)

    log_req = CreateTripIssueRequest(
        issue_type="WEATHER_DELAY",
        description="Mưa to ngập đường",
    )
    issue = service.log_issue(trip.id, log_req, user_id=1)

    with pytest.raises((BusinessRuleException, pydantic.ValidationError)):
        resolve_req = ResolveTripIssueRequest(resolution_notes="   ")
        service.resolve_issue(trip.id, issue.id, resolve_req, user_id=1)


def test_resolve_already_resolved_issue_rejection(db_session: Session):
    """Test attempting to resolve an already resolved issue raises BusinessRuleException."""
    service = IncidentService(db_session)
    trip = create_test_trip(db_session)

    log_req = CreateTripIssueRequest(
        issue_type="CARGO_DAMAGE",
        description="Thùng hàng bị xước vỏ bao bì",
    )
    issue = service.log_issue(trip.id, log_req, user_id=1)

    resolve_req = ResolveTripIssueRequest(resolution_notes="Đã kiểm tra ruột hàng nguyên vẹn")
    service.resolve_issue(trip.id, issue.id, resolve_req, user_id=1)

    # Resolve again
    with pytest.raises(BusinessRuleException) as exc_info:
        service.resolve_issue(trip.id, issue.id, resolve_req, user_id=1)
    assert "đã được giải quyết" in str(exc_info.value)


def test_trip_status_and_price_not_modified_by_incident(db_session: Session):
    """Test invariant: incident logging does NOT complete trip or alter trip properties."""
    service = IncidentService(db_session)
    trip = create_test_trip(db_session, status=TripStatus.IN_TRANSIT.value)
    initial_status = trip.status
    initial_weight = trip.cargo_weight_kg

    req = CreateTripIssueRequest(
        issue_type="ACCIDENT",
        description="Va chạm nhẹ gương chiếu hậu",
    )
    service.log_issue(trip.id, req, user_id=1)

    db_session.refresh(trip)
    assert trip.status == initial_status
    assert trip.cargo_weight_kg == initial_weight


def test_is_delayed_property_logic(db_session: Session):
    """Test User Story 2: is_delayed property calculation logic."""
    now = datetime.now()
    # 1. Active trip past estimated_end_time -> True
    trip_delayed = Trip(
        reference_code=f"TRIP-DLY-{now.timestamp()}",
        sender_name="Cong ty Delayed",
        sender_phone="0912345678",
        pickup_address="A",
        delivery_address="B",
        cargo_weight_kg=1000,
        cargo_type="Hang hoa",
        status=TripStatus.IN_TRANSIT.value,
        estimated_start_time=now - timedelta(hours=5),
        estimated_end_time=now - timedelta(hours=1),
    )
    assert trip_delayed.is_delayed is True

    # 2. Active trip before estimated_end_time -> False
    trip_on_time = Trip(
        reference_code=f"TRIP-ONT-{now.timestamp()}",
        sender_name="Cong ty On Time",
        sender_phone="0912345678",
        pickup_address="A",
        delivery_address="B",
        cargo_weight_kg=1000,
        cargo_type="Hang hoa",
        status=TripStatus.IN_TRANSIT.value,
        estimated_start_time=now - timedelta(hours=1),
        estimated_end_time=now + timedelta(hours=3),
    )
    assert trip_on_time.is_delayed is False

    # 3. Completed or Delivered trip past estimated_end_time -> False
    trip_delivered = Trip(
        reference_code=f"TRIP-DEL-{now.timestamp()}",
        sender_name="Cong ty Delivered",
        sender_phone="0912345678",
        pickup_address="A",
        delivery_address="B",
        cargo_weight_kg=1000,
        cargo_type="Hang hoa",
        status=TripStatus.DELIVERED.value,
        estimated_start_time=now - timedelta(hours=5),
        estimated_end_time=now - timedelta(hours=1),
    )
    assert trip_delivered.is_delayed is False
