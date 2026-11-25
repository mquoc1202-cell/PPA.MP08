import os
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.security import require_role, get_current_user
from src.core.exceptions import EntityNotFoundError
from src.schemas.auth import UserSession
from src.models.trip import Trip, TripStatus
from src.repositories.trip_repo import TripRepository
from src.repositories.trip_issue_repo import TripIssueRepository
from src.services.dispatch_service import DispatchService
from src.services.trip_tracking_service import TripTrackingService
from src.services.delivery_service import DeliveryService, UploadedEvidenceFile
from src.services.incident_service import IncidentService
from src.repositories.trip_event_repo import TripEventRepository
from src.repositories.trip_evidence_repo import TripEvidenceRepository
from src.schemas.trip import (
    CreateTripRequest,
    AssignTripRequest,
    ReassignTripRequest,
    RecordPickupRequest,
    RecordDepartureRequest,
    RecordDeliveryRequest,
    CompleteTripRequest,
    CreateTripIssueRequest,
    ResolveTripIssueRequest,
    RescheduleTripRequest,
    TripItem,
    TripDetailResponse,
    TripListResponse,
    TripEventsResponse,
    TripEventItem,
    TripEvidenceItem,
    TripEvidenceResponse,
    TripIssueItem,
    TripIssuesListResponse,
    TripIssueDetailResponse,
)
from src.core.exceptions import EntityNotFoundError

router = APIRouter(prefix="/trips", tags=["Trips & Dispatch API"])


def get_dispatch_service(db: Session = Depends(get_db)) -> DispatchService:
    return DispatchService(db)


def get_trip_tracking_service(db: Session = Depends(get_db)) -> TripTrackingService:
    return TripTrackingService(db)


def get_delivery_service(db: Session = Depends(get_db)) -> DeliveryService:
    return DeliveryService(db)


@router.get("", response_model=TripListResponse)
def list_trips(
    status: Optional[str] = Query(None, description="Lọc theo trạng thái chuyến (UNASSIGNED, ASSIGNED...)"),
    search: Optional[str] = Query(None, description="Tìm theo mã chuyến, người gửi, địa chỉ, loại hàng"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List trips with optional filter and search."""
    repo = TripRepository(db)
    skip = (page - 1) * page_size
    items, total = repo.filter_trips(status=status, search=search, skip=skip, limit=page_size)
    data = [TripItem.model_validate(t) for t in items]
    return TripListResponse(
        success=True,
        data=data,
        meta={"page": page, "page_size": page_size, "total_items": total},
    )


@router.post("", response_model=TripDetailResponse, status_code=status.HTTP_201_CREATED)
def create_trip(
    req: CreateTripRequest,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Create a new unassigned trip."""
    repo = TripRepository(db)
    # Generate unique reference code
    timestamp_suffix = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")
    ref_code = f"TRIP-{timestamp_suffix}"

    trip = Trip(
        reference_code=ref_code,
        sender_name=req.sender_name,
        sender_phone=req.sender_phone,
        pickup_address=req.pickup_address,
        delivery_address=req.delivery_address,
        cargo_weight_kg=req.cargo_weight_kg,
        cargo_type=req.cargo_type,
        notes=req.notes,
        status=TripStatus.UNASSIGNED.value,
    )
    saved_trip = repo.create(trip)
    return TripDetailResponse(
        success=True,
        data=TripItem.model_validate(saved_trip),
    )


@router.get("/{id}", response_model=TripDetailResponse)
def get_trip(
    id: int,
    db: Session = Depends(get_db),
):
    """Get trip details by ID."""
    repo = TripRepository(db)
    trip = repo.get_by_id(id)
    if not trip:
        raise EntityNotFoundError(f"Chuyến hàng ID {id} không tồn tại.")
    return TripDetailResponse(
        success=True,
        data=TripItem.model_validate(trip),
    )


@router.post("/{id}/assign", response_model=TripDetailResponse)
def assign_trip(
    id: int,
    req: AssignTripRequest,
    service: DispatchService = Depends(get_dispatch_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Assign truck and driver to an UNASSIGNED trip."""
    trip = service.assign_trip(id, req)
    return TripDetailResponse(
        success=True,
        data=TripItem.model_validate(trip),
    )


@router.post("/{id}/reassign", response_model=TripDetailResponse)
def reassign_trip(
    id: int,
    req: ReassignTripRequest,
    service: DispatchService = Depends(get_dispatch_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Change truck and/or driver on an ASSIGNED trip."""
    trip = service.reassign_trip(id, req)
    return TripDetailResponse(
        success=True,
        data=TripItem.model_validate(trip),
    )


@router.post("/{id}/unassign", response_model=TripDetailResponse)
def unassign_trip(
    id: int,
    service: DispatchService = Depends(get_dispatch_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Revoke assignment from an ASSIGNED trip, releasing bookings."""
    trip = service.unassign_trip(id)
    return TripDetailResponse(
        success=True,
        data=TripItem.model_validate(trip),
    )


@router.post("/{id}/pickup", response_model=TripDetailResponse)
def record_trip_pickup(
    id: int,
    req: RecordPickupRequest,
    service: TripTrackingService = Depends(get_trip_tracking_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Record actual cargo pickup (ASSIGNED -> PICKED_UP)."""
    trip = service.record_pickup(id, req, user_id=current_user.id)
    return TripDetailResponse(success=True, data=TripItem.model_validate(trip))


@router.post("/{id}/depart", response_model=TripDetailResponse)
def record_trip_departure(
    id: int,
    req: RecordDepartureRequest,
    service: TripTrackingService = Depends(get_trip_tracking_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Record actual departure (PICKED_UP -> IN_TRANSIT)."""
    trip = service.record_departure(id, req, user_id=current_user.id)
    return TripDetailResponse(success=True, data=TripItem.model_validate(trip))


@router.get("/{id}/events", response_model=TripEventsResponse)
def get_trip_events(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """Get audit timeline events for trip."""
    repo = TripRepository(db)
    trip = repo.get_by_id(id)
    if not trip:
        raise EntityNotFoundError(f"Chuyến hàng ID {id} không tồn tại.")
    event_repo = TripEventRepository(db)
    events = event_repo.get_events_for_trip(id)
    return TripEventsResponse(
        success=True,
        data=[TripEventItem.model_validate(e) for e in events],
        meta={"total": len(events), "trip_id": id},
    )


@router.post("/{id}/deliver", response_model=TripDetailResponse)
async def record_trip_delivery(
    id: int,
    actual_delivery_time: str = Form(...),
    recipient_name: Optional[str] = Form(None),
    result: str = Form("SUCCESS"),
    delivery_notes: Optional[str] = Form(None),
    evidence_files: List[UploadFile] = File(default=[]),
    service: DeliveryService = Depends(get_delivery_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Confirm cargo delivery or report delivery failure (TRN-04)."""
    deliv_dt = datetime.fromisoformat(actual_delivery_time)
    uploaded = []
    for f in evidence_files:
        if f.filename:
            content = await f.read()
            uploaded.append(
                UploadedEvidenceFile(
                    filename=f.filename,
                    content=content,
                    content_type=f.content_type or "application/octet-stream",
                    evidence_type="POD" if result.upper() == "SUCCESS" else "INCIDENT_PHOTO",
                )
            )

    req = RecordDeliveryRequest(
        actual_delivery_time=deliv_dt,
        recipient_name=recipient_name,
        result=result,
        delivery_notes=delivery_notes,
    )
    trip = service.record_delivery(id, req, files=uploaded, user_id=current_user.id)
    return TripDetailResponse(success=True, data=TripItem.model_validate(trip))


@router.post("/{id}/complete", response_model=TripDetailResponse)
def complete_trip(
    id: int,
    req: CompleteTripRequest,
    service: DeliveryService = Depends(get_delivery_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Complete trip and release resources (TRN-04)."""
    trip = service.complete_trip(id, req, user_id=current_user.id)
    return TripDetailResponse(success=True, data=TripItem.model_validate(trip))


@router.get("/{id}/evidence", response_model=TripEvidenceResponse)
def get_trip_evidence(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """Get list of POD evidence documents for a trip."""
    repo = TripRepository(db)
    trip = repo.get_by_id(id)
    if not trip:
        raise EntityNotFoundError(f"Chuyến hàng ID {id} không tồn tại.")
    evidence_repo = TripEvidenceRepository(db)
    evidences = evidence_repo.get_evidence_by_trip(id)
    items = []
    for ev in evidences:
        item = TripEvidenceItem.model_validate(ev)
        item.download_url = f"/api/v1/trips/{id}/evidence/{ev.id}/download"
        items.append(item)
    return TripEvidenceResponse(
        success=True,
        data=items,
        meta={"total": len(items), "trip_id": id},
    )


@router.post("/{id}/evidence")
async def upload_additional_evidence(
    id: int,
    file: UploadFile = File(...),
    evidence_type: str = Form("POD"),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    service: DeliveryService = Depends(get_delivery_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Upload additional evidence for a trip."""
    repo = TripRepository(db)
    trip = repo.get_by_id(id)
    if not trip:
        raise EntityNotFoundError(f"Chuyến hàng ID {id} không tồn tại.")
    content = await file.read()
    uploaded = UploadedEvidenceFile(
        filename=file.filename,
        content=content,
        content_type=file.content_type or "application/octet-stream",
        evidence_type=evidence_type,
        notes=notes,
    )
    saved_path = service._save_file_to_disk(uploaded)
    ev = TripEvidenceRepository(db).add_evidence(
        trip_id=id,
        file_path=saved_path,
        file_name=file.filename,
        file_size_bytes=len(content),
        mime_type=file.content_type or "application/octet-stream",
        evidence_type=evidence_type,
        notes=notes,
        uploaded_by_user_id=current_user.id,
    )
    db.commit()
    db.refresh(ev)
    item = TripEvidenceItem.model_validate(ev)
    item.download_url = f"/api/v1/trips/{id}/evidence/{ev.id}/download"
    return {"success": True, "data": item.model_dump()}


@router.get("/{id}/evidence/{evidence_id}/download")
def download_evidence(
    id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """Download or view evidence document."""
    evidence_repo = TripEvidenceRepository(db)
    ev = evidence_repo.get_by_id(evidence_id)
    if not ev or ev.trip_id != id:
        raise EntityNotFoundError("Tệp chứng từ không tồn tại.")
    full_path = os.path.join("src", "static", ev.file_path)
    if not os.path.exists(full_path):
        full_path = ev.file_path
        if not os.path.exists(full_path):
            raise EntityNotFoundError("Tệp vật lý không tồn tại trên hệ thống lưu trữ.")
    return FileResponse(
        full_path,
        filename=ev.file_name,
        media_type=ev.mime_type,
    )


def get_incident_service(db: Session = Depends(get_db)) -> IncidentService:
    return IncidentService(db)


@router.get("/{id}/issues", response_model=TripIssuesListResponse)
def get_trip_issues(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """Get all issues for a trip."""
    repo = TripRepository(db)
    trip = repo.get_by_id(id)
    if not trip:
        raise EntityNotFoundError(f"Chuyến hàng ID {id} không tồn tại.")
    issue_repo = TripIssueRepository(db)
    issues = issue_repo.get_issues_by_trip(id)
    items = [TripIssueItem.model_validate(i) for i in issues]
    has_open = any(i.status == "OPEN" for i in items)
    return TripIssuesListResponse(
        success=True,
        data=items,
        meta={"total": len(items), "trip_id": id, "has_open_issues": has_open},
    )


@router.post("/{id}/issues", response_model=TripIssueDetailResponse, status_code=201)
def create_trip_issue(
    id: int,
    req: CreateTripIssueRequest,
    service: IncidentService = Depends(get_incident_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Log a new incident/issue for a trip (TRN-05)."""
    issue = service.log_issue(id, req, user_id=current_user.id)
    return TripIssueDetailResponse(success=True, data=TripIssueItem.model_validate(issue))


@router.post("/{id}/issues/{issue_id}/resolve", response_model=TripIssueDetailResponse)
def resolve_trip_issue(
    id: int,
    issue_id: int,
    req: ResolveTripIssueRequest,
    service: IncidentService = Depends(get_incident_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Resolve an open incident/issue for a trip (TRN-05)."""
    issue = service.resolve_issue(id, issue_id, req, user_id=current_user.id)
    return TripIssueDetailResponse(success=True, data=TripIssueItem.model_validate(issue))


@router.post("/{id}/reschedule")
def reschedule_trip(
    id: int,
    req: RescheduleTripRequest,
    service: IncidentService = Depends(get_incident_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Reschedule trip estimated_end_time and detect future conflicts (TRN-05)."""
    trip, conflicts = service.reschedule_trip(
        trip_id=id,
        new_estimated_end_time=req.new_estimated_end_time,
        reason=req.reason,
        user_id=current_user.id,
    )
    conflict_items = []
    for c in conflicts:
        conflict_items.append({
            "trip_id": getattr(c, "trip_id", None),
            "reference_code": c.reference_code,
            "service_type": c.service_type,
            "resource_type": c.resource_type,
            "start_time": c.start_time.isoformat() if c.start_time else None,
            "end_time": c.end_time.isoformat() if c.end_time else None,
        })

    if conflicts:
        return JSONResponse(
            status_code=409,
            content={
                "success": True,
                "data": {
                    "trip_id": trip.id,
                    "new_estimated_end_time": trip.estimated_end_time.isoformat(),
                    "has_conflicts": True,
                    "conflicts": conflict_items,
                },
                "error": f"Lịch trình đã được cập nhật nhưng phát hiện xung đột với {len(conflicts)} booking tương lai. Vui lòng kiểm tra và dời hoặc gán lại xe/tài xế cho các đơn bị ảnh hưởng.",
            },
        )

    return {
        "success": True,
        "data": {
            "trip_id": trip.id,
            "new_estimated_end_time": trip.estimated_end_time.isoformat(),
            "has_conflicts": False,
            "conflicts": [],
        },
        "error": None,
    }
