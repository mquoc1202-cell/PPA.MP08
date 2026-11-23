from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.repositories.driver_repo import DriverRepository
from src.repositories.booking_repo import ResourceBookingRepository
from src.services.driver_service import DriverService
from src.schemas.driver import CreateDriverRequest, UpdateDriverRequest, ChangeDriverStatusRequest, DriverDetailResponse
from src.schemas.common import ApiResponse

router = APIRouter(prefix="/drivers", tags=["Drivers"])

def get_driver_service(db: Session = Depends(get_db)) -> DriverService:
    driver_repo = DriverRepository(db)
    booking_repo = ResourceBookingRepository(db)
    return DriverService(driver_repo, booking_repo)

@router.get("", response_model=ApiResponse[list[DriverDetailResponse]])
def list_drivers(
    status: Optional[str] = Query(None, description="Lọc theo trạng thái (ACTIVE, INACTIVE)"),
    search: Optional[str] = Query(None, description="Tìm theo mã tài xế, họ tên, hoặc số điện thoại"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DriverService = Depends(get_driver_service)
):
    items, total = service.list_drivers(status=status, search=search, page=page, page_size=page_size)
    data = [DriverDetailResponse.model_validate(d) for d in items]
    return ApiResponse(
        success=True,
        data=data,
        meta={"page": page, "page_size": page_size, "total_items": total}
    )

@router.post("", response_model=ApiResponse[DriverDetailResponse], status_code=status.HTTP_201_CREATED)
def create_driver(
    req: CreateDriverRequest,
    service: DriverService = Depends(get_driver_service)
):
    driver = service.create_driver(req)
    return ApiResponse(
        success=True,
        data=DriverDetailResponse.model_validate(driver)
    )

@router.get("/{id}", response_model=ApiResponse[DriverDetailResponse])
def get_driver(
    id: int,
    service: DriverService = Depends(get_driver_service)
):
    driver = service.get_driver_by_id(id)
    return ApiResponse(
        success=True,
        data=DriverDetailResponse.model_validate(driver)
    )

@router.put("/{id}", response_model=ApiResponse[DriverDetailResponse])
def update_driver(
    id: int,
    req: UpdateDriverRequest,
    service: DriverService = Depends(get_driver_service)
):
    driver = service.update_driver(id, req)
    return ApiResponse(
        success=True,
        data=DriverDetailResponse.model_validate(driver)
    )

@router.patch("/{id}/status", response_model=ApiResponse[DriverDetailResponse])
def change_driver_status(
    id: int,
    req: ChangeDriverStatusRequest,
    service: DriverService = Depends(get_driver_service)
):
    driver = service.change_driver_status(id, req.status, req.reason)
    return ApiResponse(
        success=True,
        data=DriverDetailResponse.model_validate(driver)
    )

@router.delete("/{id}", response_model=ApiResponse[dict])
def delete_driver(
    id: int,
    service: DriverService = Depends(get_driver_service)
):
    service.delete_driver(id)
    return ApiResponse(
        success=True,
        data={"message": f"Tài xế ID {id} đã được xóa thành công."}
    )
