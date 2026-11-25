from typing import Optional
from datetime import datetime, date
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.templates import templates
from src.core.security import get_current_user
from src.schemas.auth import UserSession
from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.booking import ResourceType, ResourceBooking, BookingStatus
from src.repositories.booking_repo import ResourceBookingRepository

router = APIRouter(prefix="/schedule", tags=["Schedule Web"])


@router.get("", response_class=HTMLResponse)
def schedule_index_view(
    request: Request,
    resource_type: str = Query("truck", pattern="^(truck|driver)$"),
    resource_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """Render giao diện tra cứu lịch trình chiếm dụng của Xe tải hoặc Tài xế."""
    trucks = db.query(Truck).filter(Truck.status != TruckStatus.INACTIVE.value).order_by(Truck.plate_number.asc()).all()
    drivers = db.query(Driver).filter(Driver.status != DriverStatus.INACTIVE.value).order_by(Driver.full_name.asc()).all()

    # Determine default resource if none provided
    selected_truck = None
    selected_driver = None

    if resource_type == "truck":
        if resource_id:
            selected_truck = db.query(Truck).filter(Truck.id == resource_id).first()
        elif trucks:
            selected_truck = trucks[0]
            resource_id = selected_truck.id
    else:
        if resource_id:
            selected_driver = db.query(Driver).filter(Driver.id == resource_id).first()
        elif drivers:
            selected_driver = drivers[0]
            resource_id = selected_driver.id

    parsed_start_date = None
    parsed_end_date = None
    if start_date:
        try:
            parsed_start_date = date.fromisoformat(start_date)
        except ValueError:
            pass
    if end_date:
        try:
            parsed_end_date = date.fromisoformat(end_date)
        except ValueError:
            pass

    bookings = []
    if resource_id:
        repo = ResourceBookingRepository(db)
        r_type = ResourceType.TRUCK.value if resource_type == "truck" else ResourceType.DRIVER.value
        bookings = repo.get_bookings_by_range(
            resource_type=r_type,
            resource_id=resource_id,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
        )

    return templates.TemplateResponse(
        request=request,
        name="schedule/index.html",
        context={
            "active_tab": "schedule",
            "current_user": current_user,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "trucks": trucks,
            "drivers": drivers,
            "selected_truck": selected_truck,
            "selected_driver": selected_driver,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "bookings": bookings,
        },
    )
