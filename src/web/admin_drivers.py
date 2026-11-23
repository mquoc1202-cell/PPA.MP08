from typing import Optional
from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.api.v1.drivers import get_driver_service
from src.services.driver_service import DriverService
from src.schemas.driver import CreateDriverRequest, UpdateDriverRequest
from src.models.driver import DriverStatus
from src.core.exceptions import DomainException

router = APIRouter(prefix="/admin/drivers", tags=["Admin Drivers Web"])
templates = Jinja2Templates(directory="src/templates")

@router.get("", response_class=HTMLResponse)
def admin_list_drivers(
    request: Request,
    status: Optional[str] = None,
    search: Optional[str] = None,
    service: DriverService = Depends(get_driver_service)
):
    drivers, total = service.list_drivers(status=status, search=search, page=1, page_size=100)
    return templates.TemplateResponse(
        "drivers/list.html",
        {
            "request": request,
            "drivers": drivers,
            "total": total,
            "status": status,
            "search": search,
            "active_tab": "drivers"
        }
    )

@router.get("/create", response_class=HTMLResponse)
def admin_create_driver_form(request: Request):
    return templates.TemplateResponse(
        "drivers/form.html",
        {"request": request, "driver": None, "active_tab": "drivers"}
    )

@router.post("/create")
def admin_create_driver_submit(
    request: Request,
    driver_code: str = Form(...),
    full_name: str = Form(...),
    phone_number: str = Form(...),
    service: DriverService = Depends(get_driver_service)
):
    try:
        req = CreateDriverRequest(
            driver_code=driver_code,
            full_name=full_name,
            phone_number=phone_number
        )
        service.create_driver(req)
        return RedirectResponse(url="/admin/drivers?success=true", status_code=status.HTTP_303_SEE_OTHER)
    except (DomainException, ValueError) as e:
        return templates.TemplateResponse(
            "drivers/form.html",
            {
                "request": request,
                "driver": None,
                "error_message": str(e),
                "active_tab": "drivers"
            },
            status_code=400
        )

@router.get("/{id}/edit", response_class=HTMLResponse)
def admin_edit_driver_form(
    id: int,
    request: Request,
    service: DriverService = Depends(get_driver_service)
):
    driver = service.get_driver_by_id(id)
    return templates.TemplateResponse(
        "drivers/form.html",
        {"request": request, "driver": driver, "active_tab": "drivers"}
    )

@router.post("/{id}/edit")
def admin_edit_driver_submit(
    id: int,
    request: Request,
    full_name: str = Form(...),
    phone_number: str = Form(...),
    status_val: Optional[str] = Form(None, alias="status"),
    service: DriverService = Depends(get_driver_service)
):
    try:
        req = UpdateDriverRequest(
            full_name=full_name,
            phone_number=phone_number
        )
        service.update_driver(id, req)
        if status_val:
            service.change_driver_status(id, DriverStatus(status_val))
        return RedirectResponse(url="/admin/drivers?updated=true", status_code=status.HTTP_303_SEE_OTHER)
    except (DomainException, ValueError) as e:
        driver = service.get_driver_by_id(id)
        return templates.TemplateResponse(
            "drivers/form.html",
            {
                "request": request,
                "driver": driver,
                "error_message": str(e),
                "active_tab": "drivers"
            },
            status_code=400
        )
