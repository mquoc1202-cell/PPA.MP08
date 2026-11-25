from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.templates import templates
from src.core.security import get_current_user
from src.schemas.auth import UserSession
from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.booking import ResourceBooking, BookingStatus

router = APIRouter(tags=["Dashboard Web"])


@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def dashboard_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    # Truck metrics
    total_trucks = db.query(Truck).count()
    active_trucks = db.query(Truck).filter(Truck.status == TruckStatus.ACTIVE.value).count()
    maintenance_trucks = db.query(Truck).filter(Truck.status == TruckStatus.MAINTENANCE.value).count()
    inactive_trucks = db.query(Truck).filter(Truck.status == TruckStatus.INACTIVE.value).count()

    # Driver metrics
    total_drivers = db.query(Driver).count()
    active_drivers = db.query(Driver).filter(Driver.status == DriverStatus.ACTIVE.value).count()
    inactive_drivers = db.query(Driver).filter(Driver.status == DriverStatus.INACTIVE.value).count()

    # Booking metrics
    active_bookings = db.query(ResourceBooking).filter(
        ResourceBooking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.IN_PROGRESS.value])
    ).count()

    # Recent items
    recent_trucks = db.query(Truck).order_by(Truck.id.desc()).limit(5).all()
    recent_drivers = db.query(Driver).order_by(Driver.id.desc()).limit(5).all()

    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "active_tab": "dashboard",
            "current_user": current_user,
            "total_trucks": total_trucks,
            "active_trucks": active_trucks,
            "maintenance_trucks": maintenance_trucks,
            "inactive_trucks": inactive_trucks,
            "total_drivers": total_drivers,
            "active_drivers": active_drivers,
            "inactive_drivers": inactive_drivers,
            "active_bookings": active_bookings,
            "recent_trucks": recent_trucks,
            "recent_drivers": recent_drivers,
        },
    )
