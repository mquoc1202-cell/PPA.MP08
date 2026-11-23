from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from src.core.logging import get_logger
from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.booking import ResourceBooking, ResourceType, BookingStatus
from src.services.truck_service import TruckService

logger = get_logger("seed")

def seed_initial_data(db: Session) -> None:
    """Populates realistic initial data for Trucks, Drivers, and Bookings if database is empty."""
    truck_count = db.query(Truck).count()
    if truck_count > 0:
        logger.info("Database already contains data, skipping seed.")
        return

    logger.info("Seeding initial demo data for TRN-01...")

    # 1. Seed Trucks
    trucks_data = [
        ("29C-123.45", "Xe thùng kín 5T", 5000, "Xe phục vụ tuyến Hà Nội - Hải Phòng", TruckStatus.ACTIVE.value),
        ("29H-567.89", "Xe tải bạt 8T", 8000, "Xe chuyên tuyến Bắc - Nam", TruckStatus.ACTIVE.value),
        ("51D-999.88", "Xe đầu kéo Container 40ft", 32000, "Vận tải cảng Cát Lái", TruckStatus.ACTIVE.value),
        ("15C-432.10", "Xe tải đông lạnh 3.5T", 3500, "Bảo dưỡng định kỳ 10,000 km", TruckStatus.MAINTENANCE.value),
        ("43C-888.99", "Xe tải ben 10T", 10000, "Tạm dừng hoạt động chờ đăng kiểm", TruckStatus.INACTIVE.value),
    ]

    truck_entities = []
    for plate, t_type, cap, desc, st in trucks_data:
        norm = TruckService.normalize_plate_number(plate)
        truck = Truck(
            plate_number=plate,
            normalized_plate=norm,
            truck_type=t_type,
            capacity_kg=cap,
            description=desc,
            status=st
        )
        db.add(truck)
        truck_entities.append(truck)

    db.commit()
    for t in truck_entities:
        db.refresh(t)

    # 2. Seed Drivers
    drivers_data = [
        ("TX001", "Nguyễn Văn An", "0912345678", DriverStatus.ACTIVE.value),
        ("TX002", "Trần Đình Bình", "0987654321", DriverStatus.ACTIVE.value),
        ("TX003", "Lê Hoàng Cường", "0905123456", DriverStatus.ACTIVE.value),
        ("TX004", "Phạm Quốc Dũng", "0933221100", DriverStatus.ACTIVE.value),
        ("TX005", "Hoàng Văn Em", "0977889900", DriverStatus.INACTIVE.value),
    ]

    driver_entities = []
    for code, name, phone, st in drivers_data:
        driver = Driver(
            driver_code=code,
            full_name=name,
            phone_number=phone,
            status=st
        )
        db.add(driver)
        driver_entities.append(driver)

    db.commit()
    for d in driver_entities:
        db.refresh(d)

    # 3. Seed Realistic Bookings
    # Booking 1: Past completed booking for truck 1 & driver 1 (Enforces Soft-Delete Guard!)
    now = datetime.now(timezone.utc)
    past_booking_truck = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck_entities[0].id,
        reference_code="TRIP-2026-PAST01",
        start_time=now - timedelta(days=5),
        end_time=now - timedelta(days=4),
        status=BookingStatus.COMPLETED.value
    )
    past_booking_driver = ResourceBooking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver_entities[0].id,
        reference_code="TRIP-2026-PAST01",
        start_time=now - timedelta(days=5),
        end_time=now - timedelta(days=4),
        status=BookingStatus.COMPLETED.value
    )

    # Booking 2: Future confirmed booking for truck 1 & driver 1 (Enforces Future Schedule Conflict Check!)
    future_booking_truck = ResourceBooking(
        resource_type=ResourceType.TRUCK.value,
        resource_id=truck_entities[0].id,
        reference_code="ORDER-2026-FUT99",
        start_time=now + timedelta(days=2),
        end_time=now + timedelta(days=4),
        status=BookingStatus.CONFIRMED.value
    )
    future_booking_driver = ResourceBooking(
        resource_type=ResourceType.DRIVER.value,
        resource_id=driver_entities[0].id,
        reference_code="ORDER-2026-FUT99",
        start_time=now + timedelta(days=2),
        end_time=now + timedelta(days=4),
        status=BookingStatus.CONFIRMED.value
    )

    db.add_all([past_booking_truck, past_booking_driver, future_booking_truck, future_booking_driver])
    db.commit()

    logger.info("Demo data successfully seeded: 5 Trucks, 5 Drivers, 4 Bookings.")
