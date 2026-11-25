from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import get_current_user
from src.schemas.auth import UserSession
from src.schemas.trip import ScheduleListResponse, BookingItem
from src.models.booking import ResourceType
from src.models.truck import Truck
from src.models.driver import Driver
from src.repositories.booking_repo import ResourceBookingRepository
from src.core.exceptions import EntityNotFoundError

router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.get("/trucks/{id}", response_model=ScheduleListResponse)
def get_truck_schedule(
    id: int = Path(..., description="ID của xe tải"),
    start_date: Optional[date] = Query(None, description="Ngày bắt đầu (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Ngày kết thúc (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """Lấy danh sách các lịch trình chiếm dụng của xe tải theo khoảng ngày."""
    truck = db.query(Truck).filter(Truck.id == id).first()
    if not truck:
        raise EntityNotFoundError(f"Xe tải với ID {id} không tồn tại.")

    repo = ResourceBookingRepository(db)
    bookings = repo.get_bookings_by_range(
        resource_type=ResourceType.TRUCK.value,
        resource_id=id,
        start_date=start_date,
        end_date=end_date,
    )
    items = [BookingItem.model_validate(b) for b in bookings]
    return ScheduleListResponse(
        success=True,
        data=items,
        meta={"total": len(items), "resource_id": id, "resource_type": ResourceType.TRUCK.value},
    )


@router.get("/drivers/{id}", response_model=ScheduleListResponse)
def get_driver_schedule(
    id: int = Path(..., description="ID của tài xế"),
    start_date: Optional[date] = Query(None, description="Ngày bắt đầu (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Ngày kết thúc (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """Lấy danh sách các lịch trình chiếm dụng của tài xế theo khoảng ngày."""
    driver = db.query(Driver).filter(Driver.id == id).first()
    if not driver:
        raise EntityNotFoundError(f"Tài xế với ID {id} không tồn tại.")

    repo = ResourceBookingRepository(db)
    bookings = repo.get_bookings_by_range(
        resource_type=ResourceType.DRIVER.value,
        resource_id=id,
        start_date=start_date,
        end_date=end_date,
    )
    items = [BookingItem.model_validate(b) for b in bookings]
    return ScheduleListResponse(
        success=True,
        data=items,
        meta={"total": len(items), "resource_id": id, "resource_type": ResourceType.DRIVER.value},
    )
