from typing import Optional, List, Tuple
from src.core.logging import get_logger
from src.core.exceptions import EntityNotFoundError, ConflictError, BusinessRuleViolationError, ScheduleConflictError
from src.models.driver import Driver, DriverStatus
from src.models.booking import ResourceType, BookingStatus
from src.repositories.driver_repo import DriverRepository
from src.repositories.booking_repo import ResourceBookingRepository
from src.schemas.driver import CreateDriverRequest, UpdateDriverRequest

logger = get_logger("driver_service")

class DriverService:
    """Service handling Driver business logic, uniqueness checks, and status guards."""

    def __init__(self, driver_repo: DriverRepository, booking_repo: ResourceBookingRepository):
        self.driver_repo = driver_repo
        self.booking_repo = booking_repo

    def get_driver_by_id(self, driver_id: int) -> Driver:
        driver = self.driver_repo.get_by_id(driver_id)
        if not driver:
            logger.warning(f"Driver not found: ID {driver_id}")
            raise EntityNotFoundError(f"Không tìm thấy tài xế với ID {driver_id}")
        return driver

    def list_drivers(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Driver], int]:
        skip = (page - 1) * page_size
        return self.driver_repo.filter_drivers(status=status, search=search, skip=skip, limit=page_size)

    def create_driver(self, req: CreateDriverRequest) -> Driver:
        code_upper = req.driver_code.strip().upper()
        logger.info(f"Creating driver with code: {code_upper}")

        # Check unique driver code
        existing = self.driver_repo.get_by_code(code_upper)
        if existing:
            logger.warning(f"Duplicate driver code attempt: {code_upper}")
            raise ConflictError(f"Mã tài xế '{code_upper}' đã tồn tại trong hệ thống.")

        driver = Driver(
            driver_code=code_upper,
            full_name=req.full_name.strip(),
            phone_number=req.phone_number.strip(),
            status=DriverStatus.ACTIVE.value
        )
        created = self.driver_repo.create(driver)
        logger.info(f"Driver created successfully with ID: {created.id}")
        return created

    def update_driver(self, driver_id: int, req: UpdateDriverRequest) -> Driver:
        driver = self.get_driver_by_id(driver_id)
        driver.full_name = req.full_name.strip()
        driver.phone_number = req.phone_number.strip()

        updated = self.driver_repo.update(driver)
        logger.info(f"Driver ID {driver_id} updated successfully")
        return updated

    def change_driver_status(self, driver_id: int, new_status: DriverStatus, reason: Optional[str] = None) -> Driver:
        driver = self.get_driver_by_id(driver_id)
        if driver.status == new_status.value:
            return driver

        logger.info(f"Request to change driver ID {driver_id} status: {driver.status} -> {new_status.value}")

        # Check guardrails when changing to INACTIVE
        if new_status == DriverStatus.INACTIVE:
            future_bookings = self.booking_repo.get_future_or_active_bookings(ResourceType.DRIVER.value, driver_id)
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
                    msg = f"Không thể đổi trạng thái: Tài xế đang trong chuyến vận tải (IN_PROGRESS)."
                else:
                    msg = f"Không thể đổi trạng thái: Tài xế đang có {len(future_bookings)} lịch phân công trong tương lai."

                logger.warning(f"Status change blocked for Driver ID {driver_id}: {msg}")
                raise ScheduleConflictError(msg, conflicting_bookings=conflicts)

        driver.status = new_status.value
        updated = self.driver_repo.update(driver)
        logger.info(f"Driver ID {driver_id} status successfully changed to {new_status.value}")
        return updated

    def delete_driver(self, driver_id: int) -> None:
        driver = self.get_driver_by_id(driver_id)
        logger.info(f"Checking soft delete guard for driver ID {driver_id}")

        # Immutable Audit Trail: Prohibit hard deletion if history exists
        has_history = self.booking_repo.has_booking_history(ResourceType.DRIVER.value, driver_id)
        if has_history:
            logger.warning(f"Hard delete prohibited for Driver ID {driver_id} due to booking history.")
            raise BusinessRuleViolationError(
                "Không thể xóa tài xế đã có lịch sử hoạt động/chuyến hàng. Vui lòng chuyển trạng thái sang INACTIVE."
            )

        self.driver_repo.delete(driver)
        logger.info(f"Driver ID {driver_id} deleted successfully (no history detected).")
