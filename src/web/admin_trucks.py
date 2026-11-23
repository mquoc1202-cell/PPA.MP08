from typing import Optional
from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.api.v1.trucks import get_truck_service
from src.services.truck_service import TruckService
from src.schemas.truck import CreateTruckRequest, UpdateTruckRequest
from src.models.truck import TruckStatus
from src.core.exceptions import DomainException

router = APIRouter(prefix="/admin/trucks", tags=["Admin Trucks Web"])
templates = Jinja2Templates(directory="src/templates")

@router.get("", response_class=HTMLResponse)
def admin_list_trucks(
    request: Request,
    status: Optional[str] = None,
    search: Optional[str] = None,
    service: TruckService = Depends(get_truck_service)
):
    trucks, total = service.list_trucks(status=status, search=search, page=1, page_size=100)
    return templates.TemplateResponse(
        request=request,
        name="trucks/list.html",
        context={
            "trucks": trucks,
            "total": total,
            "status": status,
            "search": search,
            "active_tab": "trucks"
        }
    )

@router.get("/create", response_class=HTMLResponse)
def admin_create_truck_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="trucks/form.html",
        context={"truck": None, "active_tab": "trucks"}
    )

@router.post("/create")
def admin_create_truck_submit(
    request: Request,
    plate_number: str = Form(...),
    truck_type: str = Form(...),
    capacity_kg: int = Form(...),
    description: Optional[str] = Form(None),
    service: TruckService = Depends(get_truck_service)
):
    try:
        req = CreateTruckRequest(
            plate_number=plate_number,
            truck_type=truck_type,
            capacity_kg=capacity_kg,
            description=description
        )
        service.create_truck(req)
        return RedirectResponse(url="/admin/trucks?success=true", status_code=status.HTTP_303_SEE_OTHER)
    except (DomainException, ValueError) as e:
        return templates.TemplateResponse(
            request=request,
            name="trucks/form.html",
            context={
                "truck": None,
                "error_message": str(e),
                "active_tab": "trucks"
            },
            status_code=400
        )

@router.get("/{id}/edit", response_class=HTMLResponse)
def admin_edit_truck_form(
    id: int,
    request: Request,
    service: TruckService = Depends(get_truck_service)
):
    truck = service.get_truck_by_id(id)
    return templates.TemplateResponse(
        request=request,
        name="trucks/form.html",
        context={"truck": truck, "active_tab": "trucks"}
    )

@router.post("/{id}/edit")
def admin_edit_truck_submit(
    id: int,
    request: Request,
    plate_number: str = Form(...),
    truck_type: str = Form(...),
    capacity_kg: int = Form(...),
    description: Optional[str] = Form(None),
    status_val: Optional[str] = Form(None, alias="status"),
    service: TruckService = Depends(get_truck_service)
):
    try:
        req = UpdateTruckRequest(
            plate_number=plate_number,
            truck_type=truck_type,
            capacity_kg=capacity_kg,
            description=description
        )
        service.update_truck(id, req)
        if status_val:
            service.change_truck_status(id, TruckStatus(status_val))
        return RedirectResponse(url="/admin/trucks?updated=true", status_code=status.HTTP_303_SEE_OTHER)
    except (DomainException, ValueError) as e:
        truck = service.get_truck_by_id(id)
        return templates.TemplateResponse(
            request=request,
            name="trucks/form.html",
            context={
                "truck": truck,
                "error_message": str(e),
                "active_tab": "trucks"
            },
            status_code=400
        )
