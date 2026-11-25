import os
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, Form, Depends, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.templates import templates
from src.core.security import get_current_user, require_role
from src.schemas.auth import UserSession
from src.models.trip import Trip, TripStatus
from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.repositories.trip_repo import TripRepository
from src.repositories.trip_event_repo import TripEventRepository
from src.repositories.trip_evidence_repo import TripEvidenceRepository
from src.repositories.trip_issue_repo import TripIssueRepository
from src.services.dispatch_service import DispatchService
from src.services.trip_tracking_service import TripTrackingService
from src.services.delivery_service import DeliveryService, UploadedEvidenceFile
from src.services.incident_service import IncidentService
from src.schemas.trip import (
    AssignTripRequest,
    ReassignTripRequest,
    RecordPickupRequest,
    RecordDepartureRequest,
    RecordDeliveryRequest,
    CompleteTripRequest,
    CreateTripIssueRequest,
    ResolveTripIssueRequest,
)
from src.core.exceptions import DomainException, ScheduleConflictError, EntityNotFoundError

router = APIRouter(prefix="/trips", tags=["Trips Web"])


@router.get("", response_class=HTMLResponse)
def trips_list_view(
    request: Request,
    status: Optional[str] = None,
    filter_mode: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """Render list of trips with status filtering, issue/delay filters, and search."""
    repo = TripRepository(db)
    is_delayed = True if filter_mode == "delayed" else None
    has_issues = True if filter_mode == "issues" else None

    trips, total = repo.filter_trips(
        status=status,
        search=search,
        has_issues=has_issues,
        is_delayed=is_delayed,
        skip=0,
        limit=100,
    )

    # Count trips by key statuses and operational alerts for tabs
    unassigned_count = db.query(Trip).filter(Trip.status == TripStatus.UNASSIGNED.value).count()
    assigned_count = db.query(Trip).filter(Trip.status == TripStatus.ASSIGNED.value).count()
    picked_up_count = db.query(Trip).filter(Trip.status == TripStatus.PICKED_UP.value).count()
    in_transit_count = db.query(Trip).filter(Trip.status == TripStatus.IN_TRANSIT.value).count()
    delivered_count = db.query(Trip).filter(Trip.status == TripStatus.DELIVERED.value).count()
    completed_count = db.query(Trip).filter(Trip.status == TripStatus.COMPLETED.value).count()
    delayed_count = repo.count_delayed_trips()
    issues_count = repo.count_trips_with_open_issues()

    return templates.TemplateResponse(
        request=request,
        name="trips/list.html",
        context={
            "active_tab": "trips",
            "current_user": current_user,
            "trips": trips,
            "total": total,
            "status": status,
            "filter_mode": filter_mode,
            "search": search,
            "unassigned_count": unassigned_count,
            "assigned_count": assigned_count,
            "picked_up_count": picked_up_count,
            "in_transit_count": in_transit_count,
            "delivered_count": delivered_count,
            "completed_count": completed_count,
            "delayed_count": delayed_count,
            "issues_count": issues_count,
        },
    )


@router.get("/{id}/dispatch", response_class=HTMLResponse)
def trip_dispatch_form(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Render dispatch form for an UNASSIGNED trip."""
    trip_repo = TripRepository(db)
    trip = trip_repo.get_by_id(id)
    if not trip:
        return RedirectResponse(url="/trips?error=not_found", status_code=status.HTTP_303_SEE_OTHER)

    # Active trucks and drivers
    trucks = db.query(Truck).filter(Truck.status == TruckStatus.ACTIVE.value).order_by(Truck.capacity_kg.asc()).all()
    drivers = db.query(Driver).filter(Driver.status == DriverStatus.ACTIVE.value).order_by(Driver.full_name.asc()).all()

    now = datetime.now()
    default_start = (now + timedelta(days=1)).strftime("%Y-%m-%dT08:00")
    default_end = (now + timedelta(days=1)).strftime("%Y-%m-%dT17:00")

    return templates.TemplateResponse(
        request=request,
        name="trips/dispatch.html",
        context={
            "active_tab": "trips",
            "current_user": current_user,
            "trip": trip,
            "trucks": trucks,
            "drivers": drivers,
            "default_start": default_start,
            "default_end": default_end,
            "error_message": None,
            "conflict_error": None,
            "is_reassign": (trip.status == TripStatus.ASSIGNED.value),
        },
    )


@router.post("/{id}/dispatch")
def trip_dispatch_submit(
    id: int,
    request: Request,
    truck_id: int = Form(...),
    driver_id: int = Form(...),
    start_time_str: str = Form(..., alias="start_time"),
    end_time_str: str = Form(..., alias="end_time"),
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Handle dispatch submission for UNASSIGNED or ASSIGNED (reassign)."""
    service = DispatchService(db)
    trip_repo = TripRepository(db)
    trip = trip_repo.get_by_id(id)
    if not trip:
        return RedirectResponse(url="/trips?error=not_found", status_code=status.HTTP_303_SEE_OTHER)

    try:
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)

        if trip.status == TripStatus.ASSIGNED.value:
            service.reassign_trip(
                trip_id=id,
                req=ReassignTripRequest(
                    truck_id=truck_id,
                    driver_id=driver_id,
                    start_time=start_time,
                    end_time=end_time,
                ),
            )
        else:
            service.assign_trip(
                trip_id=id,
                req=AssignTripRequest(
                    truck_id=truck_id,
                    driver_id=driver_id,
                    start_time=start_time,
                    end_time=end_time,
                ),
            )
        return RedirectResponse(url="/trips?success=dispatched", status_code=status.HTTP_303_SEE_OTHER)
    except ScheduleConflictError as e:
        trucks = db.query(Truck).filter(Truck.status == TruckStatus.ACTIVE.value).all()
        drivers = db.query(Driver).filter(Driver.status == DriverStatus.ACTIVE.value).all()
        return templates.TemplateResponse(
            request=request,
            name="trips/dispatch.html",
            context={
                "active_tab": "trips",
                "current_user": current_user,
                "trip": trip,
                "trucks": trucks,
                "drivers": drivers,
                "default_start": start_time_str,
                "default_end": end_time_str,
                "error_message": None,
                "conflict_error": {
                    "message": e.message,
                    "bookings": e.conflicting_bookings,
                },
                "is_reassign": (trip.status == TripStatus.ASSIGNED.value),
            },
            status_code=409,
        )
    except (DomainException, ValueError) as e:
        trucks = db.query(Truck).filter(Truck.status == TruckStatus.ACTIVE.value).all()
        drivers = db.query(Driver).filter(Driver.status == DriverStatus.ACTIVE.value).all()
        return templates.TemplateResponse(
            request=request,
            name="trips/dispatch.html",
            context={
                "active_tab": "trips",
                "current_user": current_user,
                "trip": trip,
                "trucks": trucks,
                "drivers": drivers,
                "default_start": start_time_str,
                "default_end": end_time_str,
                "error_message": str(e),
                "conflict_error": None,
                "is_reassign": (trip.status == TripStatus.ASSIGNED.value),
            },
            status_code=400,
        )


@router.post("/{id}/unassign")
def trip_unassign_submit(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Revoke assignment from an ASSIGNED trip."""
    service = DispatchService(db)
    try:
        service.unassign_trip(id)
        return RedirectResponse(url="/trips?success=unassigned", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return RedirectResponse(url=f"/trips?error={str(e)}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{id}/pickup", response_class=HTMLResponse)
def trip_pickup_form(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Render pickup confirmation form."""
    trip_repo = TripRepository(db)
    trip = trip_repo.get_by_id(id)
    if not trip:
        return RedirectResponse(url="/trips?error=not_found", status_code=status.HTTP_303_SEE_OTHER)

    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    return templates.TemplateResponse(
        request=request,
        name="trips/pickup.html",
        context={
            "active_tab": "trips",
            "current_user": current_user,
            "trip": trip,
            "default_pickup_time": now_str,
            "handover_person": "",
            "actual_weight": trip.cargo_weight_kg,
            "cargo_condition": "Nguyên đai nguyên kiện",
            "discrepancy_notes": "",
            "error_message": None,
        },
    )


@router.post("/{id}/pickup")
def trip_pickup_submit(
    id: int,
    request: Request,
    actual_pickup_time: str = Form(...),
    handover_person: str = Form(...),
    actual_cargo_weight_kg: int = Form(...),
    cargo_condition: str = Form("Nguyên đai nguyên kiện"),
    discrepancy_notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Handle pickup confirmation submission."""
    service = TripTrackingService(db)
    trip_repo = TripRepository(db)
    trip = trip_repo.get_by_id(id)
    if not trip:
        return RedirectResponse(url="/trips?error=not_found", status_code=status.HTTP_303_SEE_OTHER)

    try:
        pickup_dt = datetime.fromisoformat(actual_pickup_time)
        service.record_pickup(
            trip_id=id,
            req=RecordPickupRequest(
                actual_pickup_time=pickup_dt,
                handover_person=handover_person,
                actual_cargo_weight_kg=actual_cargo_weight_kg,
                cargo_condition=cargo_condition,
                discrepancy_notes=discrepancy_notes,
            ),
            user_id=current_user.id,
        )
        return RedirectResponse(url=f"/trips/{id}?success=picked_up", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="trips/pickup.html",
            context={
                "active_tab": "trips",
                "current_user": current_user,
                "trip": trip,
                "default_pickup_time": actual_pickup_time,
                "handover_person": handover_person,
                "actual_weight": actual_cargo_weight_kg,
                "cargo_condition": cargo_condition,
                "discrepancy_notes": discrepancy_notes or "",
                "error_message": str(e),
            },
            status_code=400,
        )


@router.post("/{id}/depart")
def trip_depart_submit(
    id: int,
    request: Request,
    actual_depart_time: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Handle departure confirmation (PICKED_UP -> IN_TRANSIT)."""
    service = TripTrackingService(db)
    try:
        depart_dt = datetime.fromisoformat(actual_depart_time) if actual_depart_time else datetime.now()
        service.record_departure(
            trip_id=id,
            req=RecordDepartureRequest(
                actual_depart_time=depart_dt,
                notes=notes,
            ),
            user_id=current_user.id,
        )
        return RedirectResponse(url=f"/trips/{id}?success=in_transit", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return RedirectResponse(url=f"/trips/{id}?error={str(e)}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{id}", response_class=HTMLResponse)
def trip_detail_view(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """Render trip detail with timeline history, POD evidence, and incidents."""
    trip_repo = TripRepository(db)
    event_repo = TripEventRepository(db)
    evidence_repo = TripEvidenceRepository(db)
    issue_repo = TripIssueRepository(db)

    trip = trip_repo.get_by_id(id)
    if not trip:
        return RedirectResponse(url="/trips?error=not_found", status_code=status.HTTP_303_SEE_OTHER)

    events = event_repo.get_events_for_trip(id)
    evidences = evidence_repo.get_evidence_by_trip(id)
    issues = issue_repo.get_issues_by_trip(id)
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    default_reschedule_dt = (trip.estimated_end_time or datetime.now()) + timedelta(hours=2)
    default_reschedule_str = default_reschedule_dt.strftime("%Y-%m-%dT%H:%M")

    return templates.TemplateResponse(
        request=request,
        name="trips/detail.html",
        context={
            "active_tab": "trips",
            "current_user": current_user,
            "trip": trip,
            "events": events,
            "evidences": evidences,
            "issues": issues,
            "default_depart_time": now_str,
            "default_complete_time": now_str,
            "default_reschedule_time": default_reschedule_str,
            "default_issue_time": now_str,
            "conflict_count": request.query_params.get("conflict_count"),
            "success": request.query_params.get("success"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/{id}/deliver", response_class=HTMLResponse)
def trip_deliver_form(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Render cargo delivery confirmation form (TRN-04)."""
    trip_repo = TripRepository(db)
    trip = trip_repo.get_by_id(id)
    if not trip:
        return RedirectResponse(url="/trips?error=not_found", status_code=status.HTTP_303_SEE_OTHER)

    if trip.status != TripStatus.IN_TRANSIT.value:
        return RedirectResponse(
            url=f"/trips/{id}?error=Chỉ có thể ghi nhận giao hàng khi chuyến đang ở trạng thái IN_TRANSIT.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")

    return templates.TemplateResponse(
        request=request,
        name="trips/deliver.html",
        context={
            "active_tab": "trips",
            "current_user": current_user,
            "trip": trip,
            "default_delivery_time": now_str,
            "recipient_name": "",
            "result": "SUCCESS",
            "delivery_notes": "",
            "error_message": None,
        },
    )


@router.post("/{id}/deliver")
async def trip_deliver_submit(
    id: int,
    request: Request,
    actual_delivery_time: str = Form(...),
    recipient_name: Optional[str] = Form(None),
    result: str = Form("SUCCESS"),
    delivery_notes: Optional[str] = Form(None),
    evidence_files: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Handle cargo delivery submission (TRN-04)."""
    trip_repo = TripRepository(db)
    trip = trip_repo.get_by_id(id)
    if not trip:
        return RedirectResponse(url="/trips?error=not_found", status_code=status.HTTP_303_SEE_OTHER)

    service = DeliveryService(db)
    try:
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
        service.record_delivery(trip_id=id, req=req, files=uploaded, user_id=current_user.id)
        if result.upper() == "SUCCESS":
            return RedirectResponse(url=f"/trips/{id}?success=delivered", status_code=status.HTTP_303_SEE_OTHER)
        else:
            return RedirectResponse(url=f"/trips/{id}?success=delivery_failed", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="trips/deliver.html",
            context={
                "active_tab": "trips",
                "current_user": current_user,
                "trip": trip,
                "default_delivery_time": actual_delivery_time,
                "recipient_name": recipient_name or "",
                "result": result,
                "delivery_notes": delivery_notes or "",
                "error_message": str(e),
            },
            status_code=400,
        )


@router.post("/{id}/complete")
def trip_complete_submit(
    id: int,
    request: Request,
    actual_completed_time: str = Form(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Handle trip completion (DELIVERED -> COMPLETED)."""
    service = DeliveryService(db)
    try:
        comp_dt = datetime.fromisoformat(actual_completed_time)
        service.complete_trip(
            trip_id=id,
            req=CompleteTripRequest(
                actual_completed_time=comp_dt,
                notes=notes,
            ),
            user_id=current_user.id,
        )
        return RedirectResponse(url=f"/trips/{id}?success=completed", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return RedirectResponse(url=f"/trips/{id}?error={str(e)}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{id}/evidence")
async def trip_upload_evidence(
    id: int,
    request: Request,
    file: UploadFile = File(...),
    evidence_type: str = Form("POD"),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Upload additional evidence file from web UI."""
    trip_repo = TripRepository(db)
    trip = trip_repo.get_by_id(id)
    if not trip:
        return RedirectResponse(url="/trips?error=not_found", status_code=status.HTTP_303_SEE_OTHER)

    service = DeliveryService(db)
    try:
        content = await file.read()
        uploaded = UploadedEvidenceFile(
            filename=file.filename,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            evidence_type=evidence_type,
            notes=notes,
        )
        saved_path = service._save_file_to_disk(uploaded)
        TripEvidenceRepository(db).add_evidence(
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
        return RedirectResponse(url=f"/trips/{id}?success=evidence_uploaded", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return RedirectResponse(url=f"/trips/{id}?error={str(e)}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{id}/evidence/{evidence_id}/download")
def trip_download_evidence(
    id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """Download or view an evidence document via Web."""
    evidence_repo = TripEvidenceRepository(db)
    ev = evidence_repo.get_by_id(evidence_id)
    if not ev or ev.trip_id != id:
        return RedirectResponse(url=f"/trips/{id}?error=Tệp chứng từ không tồn tại.", status_code=status.HTTP_303_SEE_OTHER)

    full_path = os.path.join("src", "static", ev.file_path)
    if not os.path.exists(full_path):
        full_path = ev.file_path
        if not os.path.exists(full_path):
            return RedirectResponse(url=f"/trips/{id}?error=Tệp vật lý không tồn tại trên máy chủ.", status_code=status.HTTP_303_SEE_OTHER)

    return FileResponse(
        full_path,
        filename=ev.file_name,
        media_type=ev.mime_type,
    )


@router.post("/{id}/issues")
def trip_create_issue_submit(
    id: int,
    request: Request,
    issue_type: str = Form(...),
    description: str = Form(...),
    occurred_at: Optional[str] = Form(None),
    handled_by: Optional[str] = Form(None),
    estimated_resolution_time: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Handle creation of a new trip issue from Web UI (TRN-05)."""
    service = IncidentService(db)
    try:
        occ_dt = datetime.fromisoformat(occurred_at) if occurred_at else datetime.now(timezone.utc)
        res_dt = datetime.fromisoformat(estimated_resolution_time) if estimated_resolution_time else None
        req = CreateTripIssueRequest(
            issue_type=issue_type,
            description=description,
            occurred_at=occ_dt,
            handled_by=handled_by,
            estimated_resolution_time=res_dt,
        )
        service.log_issue(id, req, user_id=current_user.id)
        return RedirectResponse(url=f"/trips/{id}?success=issue_logged", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return RedirectResponse(url=f"/trips/{id}?error={str(e)}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{id}/issues/{issue_id}/resolve")
def trip_resolve_issue_submit(
    id: int,
    issue_id: int,
    request: Request,
    resolution_notes: str = Form(...),
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Handle resolution of an open trip issue from Web UI (TRN-05)."""
    service = IncidentService(db)
    try:
        req = ResolveTripIssueRequest(resolution_notes=resolution_notes)
        service.resolve_issue(id, issue_id, req, user_id=current_user.id)
        return RedirectResponse(url=f"/trips/{id}?success=issue_resolved", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return RedirectResponse(url=f"/trips/{id}?error={str(e)}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{id}/reschedule")
def trip_reschedule_submit(
    id: int,
    request: Request,
    new_estimated_end_time: str = Form(...),
    reason: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    """Handle extending estimated_end_time and detecting future conflicts from Web UI (TRN-05)."""
    service = IncidentService(db)
    try:
        new_end_dt = datetime.fromisoformat(new_estimated_end_time)
        trip, conflicts = service.reschedule_trip(id, new_end_dt, reason, user_id=current_user.id)
        if conflicts:
            return RedirectResponse(
                url=f"/trips/{id}?success=rescheduled_with_conflict&conflict_count={len(conflicts)}",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        return RedirectResponse(url=f"/trips/{id}?success=rescheduled", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return RedirectResponse(url=f"/trips/{id}?error={str(e)}", status_code=status.HTTP_303_SEE_OTHER)
