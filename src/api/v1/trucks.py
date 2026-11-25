from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.security import require_role
from src.schemas.auth import UserSession
from src.repositories.truck_repo import TruckRepository
from src.repositories.booking_repo import ResourceBookingRepository
from src.services.truck_service import TruckService
from src.schemas.truck import (
    CreateTruckRequest,
    UpdateTruckRequest,
    ChangeTruckStatusRequest,
    TruckDetailResponse,
)
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/trucks", tags=["Trucks"])


def get_truck_service(db: Session = Depends(get_db)) -> TruckService:
    truck_repo = TruckRepository(db)
    booking_repo = ResourceBookingRepository(db)
    return TruckService(truck_repo, booking_repo)


@router.get("", response_model=ApiResponse[list[TruckDetailResponse]])
def list_trucks(
    status: Optional[str] = Query(None, description="Lọc theo trạng thái (ACTIVE, MAINTENANCE, INACTIVE)"),
    search: Optional[str] = Query(None, description="Tìm theo biển số hoặc loại xe"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TruckService = Depends(get_truck_service),
):
    items, total = service.list_trucks(status=status, search=search, page=page, page_size=page_size)
    data = [TruckDetailResponse.model_validate(t) for t in items]
    return ApiResponse(
        success=True,
        data=data,
        meta={"page": page, "page_size": page_size, "total_items": total},
    )


@router.post("", response_model=ApiResponse[TruckDetailResponse], status_code=status.HTTP_201_CREATED)
def create_truck(
    req: CreateTruckRequest,
    service: TruckService = Depends(get_truck_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    truck = service.create_truck(req)
    return ApiResponse(
        success=True,
        data=TruckDetailResponse.model_validate(truck),
    )


@router.get("/{id}", response_model=ApiResponse[TruckDetailResponse])
def get_truck(
    id: int,
    service: TruckService = Depends(get_truck_service),
):
    truck = service.get_truck_by_id(id)
    return ApiResponse(
        success=True,
        data=TruckDetailResponse.model_validate(truck),
    )


@router.put("/{id}", response_model=ApiResponse[TruckDetailResponse])
def update_truck(
    id: int,
    req: UpdateTruckRequest,
    service: TruckService = Depends(get_truck_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    truck = service.update_truck(id, req)
    return ApiResponse(
        success=True,
        data=TruckDetailResponse.model_validate(truck),
    )


@router.patch("/{id}/status", response_model=ApiResponse[TruckDetailResponse])
def change_truck_status(
    id: int,
    req: ChangeTruckStatusRequest,
    service: TruckService = Depends(get_truck_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    truck = service.change_truck_status(id, req.status, req.reason)
    return ApiResponse(
        success=True,
        data=TruckDetailResponse.model_validate(truck),
    )


@router.delete("/{id}", response_model=ApiResponse[dict])
def delete_truck(
    id: int,
    service: TruckService = Depends(get_truck_service),
    current_user: UserSession = Depends(require_role(["DSP"])),
):
    service.delete_truck(id)
    return ApiResponse(
        success=True,
        data={"message": f"Xe ID {id} đã được xóa thành công."},
    )
