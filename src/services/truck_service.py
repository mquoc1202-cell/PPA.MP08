import re
from typing import Optional, List, Tuple
from src.core.logging import get_logger
from src.core.exceptions import EntityNotFoundError, ConflictError, BusinessRuleViolationError, ScheduleConflictError
from src.models.truck import Truck, TruckStatus
from src.models.booking import ResourceType, BookingStatus
from src.repositories.truck_repo import TruckRepository
from src.repositories.booking_repo import ResourceBookingRepository
from src.schemas.truck import CreateTruckRequest, UpdateTruckRequest

logger = get_logger("truck_service")

class TruckService:
    """Service handling Truck business logic, plate normalization, capacity constraints, and status guards."""

    def __init__(self, truck_repo: TruckRepository, booking_repo: ResourceBookingRepository):
        self.truck_repo = truck_repo
        self.booking_repo = booking_repo

    @staticmethod
    def normalize_plate_number(raw_plate: str) -> str:
        """
        Normalizes a license plate number by stripping non-alphanumeric chars and converting to uppercase.
        Example: '29C-123.45' -> '29C12345', ' 51D - 999.88 ' -> '51D99988'.
        """
        if not raw_plate:
            return ""
        return re.sub(r"[^A-Za-z0-9]", "", raw_plate).upper()

    def get_truck_by_id(self, truck_id: int) -> Truck:
        truck = self.truck_repo.get_by_id(truck_id)
        if not truck:
            logger.warning(f"Truck not found: ID {truck_id}")
            raise EntityNotFoundError(f"Không tìm thấy xe với ID {truck_id}")
        return truck

    def list_trucks(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Truck], int]:
        skip = (page - 1) * page_size
        return self.truck_repo.filter_trucks(status=status, search=search, skip=skip, limit=page_size)

    def create_truck(self, req: CreateTruckRequest) -> Truck:
        normalized = self.normalize_plate_number(req.plate_number)
        logger.info(f"Creating truck with plate: {req.plate_number} (normalized: {normalized})")

        # Check unique constraint on normalized plate
        existing = self.truck_repo.get_by_normalized_plate(normalized)
        if existing:
            logger.warning(f"Duplicate truck plate attempt: {normalized}")
            raise ConflictError(f"Biển số xe '{req.plate_number}' (chuẩn hóa: '{normalized}') đã tồn tại trong hệ thống.")

        truck = Truck(
            plate_number=req.plate_number.strip(),
            normalized_plate=normalized,
            truck_type=req.truck_type.strip(),
            capacity_kg=req.capacity_kg,
            description=req.description.strip() if req.description else None,
            status=TruckStatus.ACTIVE.value
        )
        created = self.truck_repo.create(truck)
        logger.info(f"Truck created successfully with ID: {created.id}")
        return created

    def update_truck(self, truck_id: int, req: UpdateTruckRequest) -> Truck:
        truck = self.get_truck_by_id(truck_id)
        normalized = self.normalize_plate_number(req.plate_number)

        if normalized != truck.normalized_plate:
            existing = self.truck_repo.get_by_normalized_plate(normalized)
            if existing and existing.id != truck_id:
                raise ConflictError(f"Biển số xe '{req.plate_number}' đã trùng với xe khác.")

        truck.plate_number = req.plate_number.strip()
        truck.normalized_plate = normalized
        truck.truck_type = req.truck_type.strip()
        truck.capacity_kg = req.capacity_kg
        truck.description = req.description.strip() if req.description else None

        updated = self.truck_repo.update(truck)
        logger.info(f"Truck ID {truck_id} updated successfully")
        return updated

    def change_truck_status(self, truck_id: int, new_status: TruckStatus, reason: Optional[str] = None) -> Truck:
        truck = self.get_truck_by_id(truck_id)
        if truck.status == new_status.value:
            return truck

        logger.info(f"Request to change truck ID {truck_id} status: {truck.status} -> {new_status.value}")

        # Check guardrails when changing to MAINTENANCE or INACTIVE
        if new_status in (TruckStatus.MAINTENANCE, TruckStatus.INACTIVE):
            future_bookings = self.booking_repo.get_future_or_active_bookings(ResourceType.TRUCK.value, truck_id)
            if future_bookings:
                conflicts = [
                    {
                        "booking_id": b.id,
                        "reference_code": b.reference_code,
                        "status": b.status,
                        "start_time": b.start_time.isoformat(),
                        "end_time": b.end_time.isoformat()
                    }
                    for b in future_bookings
                ]
                in_progress = any(b.status == BookingStatus.IN_PROGRESS.value for b in future_bookings)
                if in_progress:
                    msg = f"Không thể đổi trạng thái: Xe đang trong chuyến vận tải (IN_PROGRESS)."
                else:
                    msg = f"Không thể đổi trạng thái: Xe đang có {len(future_bookings)} lịch phân công trong tương lai."
                
                logger.warning(f"Status change blocked for Truck ID {truck_id}: {msg}")
                raise ScheduleConflictError(msg, conflicting_bookings=conflicts)

        truck.status = new_status.value
        updated = self.truck_repo.update(truck)
        logger.info(f"Truck ID {truck_id} status successfully changed to {new_status.value}")
        return updated

    def delete_truck(self, truck_id: int) -> None:
        truck = self.get_truck_by_id(truck_id)
        logger.info(f"Checking soft delete guard for truck ID {truck_id}")

        # Immutable Audit Trail: Prohibit hard deletion if history exists
        has_history = self.booking_repo.has_booking_history(ResourceType.TRUCK.value, truck_id)
        if has_history:
            logger.warning(f"Hard delete prohibited for Truck ID {truck_id} due to booking history.")
            raise BusinessRuleViolationError(
                "Không thể xóa xe đã có lịch sử hoạt động/chuyến hàng. Vui lòng chuyển trạng thái sang INACTIVE."
            )

        self.truck_repo.delete(truck)
        logger.info(f"Truck ID {truck_id} deleted successfully (no history detected).")
