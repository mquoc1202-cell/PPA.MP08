from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from src.core.logging import get_logger
from src.core.security import hash_password
from src.models.truck import Truck, TruckStatus
from src.models.driver import Driver, DriverStatus
from src.models.booking import ResourceBooking, ResourceType, BookingStatus, ServiceType
from src.models.user import User, UserRole
from src.models.trip import Trip, TripStatus
from src.services.truck_service import TruckService

logger = get_logger("seed")


def seed_initial_data(db: Session) -> None:
    """Populates realistic initial data for Trucks, Drivers, Bookings, Users, and Trips if empty."""

    # 1. Seed Trucks, Drivers, and Bookings if Trucks empty
    truck_count = db.query(Truck).count()
    if truck_count == 0:
        logger.info("Seeding initial demo data for TRN-01 (Trucks, Drivers, Bookings)...")

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
                status=st,
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
                status=st,
            )
            db.add(driver)
            driver_entities.append(driver)

        db.commit()
        for d in driver_entities:
            db.refresh(d)

        # 3. Seed Realistic Bookings
        now = datetime.now(timezone.utc)
        past_booking_truck = ResourceBooking(
            resource_type=ResourceType.TRUCK.value,
            resource_id=truck_entities[0].id,
            reference_code="TRIP-2026-PAST01",
            service_type=ServiceType.FREIGHT.value,
            start_time=now - timedelta(days=5),
            end_time=now - timedelta(days=4),
            status=BookingStatus.COMPLETED.value,
        )
        past_booking_driver = ResourceBooking(
            resource_type=ResourceType.DRIVER.value,
            resource_id=driver_entities[0].id,
            reference_code="TRIP-2026-PAST01",
            service_type=ServiceType.FREIGHT.value,
            start_time=now - timedelta(days=5),
            end_time=now - timedelta(days=4),
            status=BookingStatus.COMPLETED.value,
        )

        future_booking_truck = ResourceBooking(
            resource_type=ResourceType.TRUCK.value,
            resource_id=truck_entities[0].id,
            reference_code="ORDER-2026-FUT99",
            service_type=ServiceType.FREIGHT.value,
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=4),
            status=BookingStatus.CONFIRMED.value,
        )
        future_booking_driver = ResourceBooking(
            resource_type=ResourceType.DRIVER.value,
            resource_id=driver_entities[0].id,
            reference_code="ORDER-2026-FUT99",
            service_type=ServiceType.FREIGHT.value,
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=4),
            status=BookingStatus.CONFIRMED.value,
        )

        db.add_all([past_booking_truck, past_booking_driver, future_booking_truck, future_booking_driver])
        db.commit()
        logger.info("Demo data successfully seeded: 5 Trucks, 5 Drivers, 4 Bookings.")

    # 4. Seed Users (Feature 002: User Auth & Access Control)
    user_count = db.query(User).count()
    if user_count == 0:
        logger.info("Seeding demo users (dsp_user, sal_user, mgr_user)...")
        demo_pwd_hash = hash_password("password123")
        users_data = [
            ("dsp_user", demo_pwd_hash, "Nguyễn Văn Điều Phối", UserRole.DSP.value),
            ("sal_user", demo_pwd_hash, "Trần Thị Kinh Doanh", UserRole.SAL.value),
            ("mgr_user", demo_pwd_hash, "Lê Quản Lý Đội Xe", UserRole.MGR.value),
            ("dsp", demo_pwd_hash, "Nguyễn Văn Điều Phối", UserRole.DSP.value),
            ("sal", demo_pwd_hash, "Trần Thị Kinh Doanh", UserRole.SAL.value),
            ("mgr", demo_pwd_hash, "Lê Quản Lý Đội Xe", UserRole.MGR.value),
        ]
        for username, pwd_hash, full_name, role in users_data:
            user = User(
                username=username,
                password_hash=pwd_hash,
                full_name=full_name,
                role=role,
                is_active=True,
            )
            db.add(user)
        db.commit()
        logger.info("Demo users successfully seeded: dsp_user, sal_user, mgr_user (password: password123).")

    # 5. Seed Trips (Feature 003: TRN-02 Dispatch & Schedule Management)
    trip_count = db.query(Trip).count()
    if trip_count == 0:
        logger.info("Seeding initial demo trips for TRN-02...")
        now = datetime.now(timezone.utc)
        trips_data = [
            (
                "TRIP-2026-001",
                "Công ty CP May Xuất khẩu Hà Nội",
                "0912345678",
                "Kho A, KCN Nội Bài, Sóc Sơn, Hà Nội",
                "Cảng Hải Phòng, Ngô Quyền, Hải Phòng",
                4500,
                "Hàng may mặc xuất khẩu",
                None,
                None,
                TripStatus.UNASSIGNED.value,
                None,
                None,
                "Yêu cầu bạt che mưa kín nước",
            ),
            (
                "TRIP-2026-002",
                "Tập đoàn Điện tử Viễn thông",
                "0987654321",
                "KCN Yên Phong, Bắc Ninh",
                "Cảng Đình Vũ, Hải Phòng",
                7200,
                "Linh kiện điện tử bán dẫn",
                None,
                None,
                TripStatus.UNASSIGNED.value,
                None,
                None,
                "Hàng giá trị cao, đi cao tốc Hà Nội - Hải Phòng",
            ),
            (
                "TRIP-2026-003",
                "Công ty TNHH Thép Việt Nhật",
                "0905112233",
                "Nhà máy thép, Vũng Áng, Hà Tĩnh",
                "Cầu Nhật Lệ, Đồng Hới, Quảng Bình",
                28000,
                "Thép cuộn công nghiệp",
                None,
                None,
                TripStatus.UNASSIGNED.value,
                None,
                None,
                "Yêu cầu xe đầu kéo tải trọng lớn",
            ),
            (
                "ORDER-2026-FUT99",
                "Công ty Nông sản Ba Vì",
                "0933445566",
                "Nông trường Ba Vì, Hà Nội",
                "Siêu thị BigC Thăng Long, Cầu Giấy, Hà Nội",
                3000,
                "Rau củ quả tươi sống",
                now + timedelta(days=2),
                now + timedelta(days=4),
                TripStatus.ASSIGNED.value,
                1,
                1,
                "Đơn đã gán xe 29C-123.45 và tài xế TX001",
            ),
            (
                "TRIP-2026-005",
                "Công ty Bê tông Xây dựng Thăng Long",
                "0977889911",
                "Mỏ đá Lương Sơn, Hòa Bình",
                "Công trường Vành đai 4, Hoài Đức, Hà Nội",
                12000,
                "Cát và đá dăm xây dựng",
                None,
                None,
                TripStatus.UNASSIGNED.value,
                None,
                None,
                "Đơn tải trọng lớn 12T",
            ),
            (
                "TRIP-2026-PKUP",
                "Công ty Dệt may Phong Phú",
                "0911223388",
                "Kho Quận 9, TP.HCM",
                "Kho ICD Tân Cảng Sóng Thần, Bình Dương",
                3200,
                "Vải cuộn dệt kim",
                now - timedelta(hours=3),
                now + timedelta(hours=5),
                TripStatus.PICKED_UP.value,
                2,
                2,
                "Đã nhận hàng lúc 07:30, sẵn sàng xuất phát",
            ),
            (
                "TRIP-2026-TRNST",
                "Công ty Thiết bị Y tế MedTech",
                "0944556677",
                "KCN VSIP 1, Bình Dương",
                "Bệnh viện Đa khoa Tỉnh Bình Thuận",
                2500,
                "Thiết bị y tế khử khuẩn",
                now - timedelta(hours=5),
                now + timedelta(hours=8),
                TripStatus.IN_TRANSIT.value,
                3,
                3,
                "Đang lưu thông trên Quốc lộ 1A",
            ),
            (
                "TRIP-2026-DELIV",
                "Công ty Điện máy Gia dụng Sunhouse",
                "0988776655",
                "Tổng kho Quang Minh, Mê Linh, Hà Nội",
                "Đại lý Điện máy Xanh, TP. Bắc Giang",
                1800,
                "Thiết bị nhà bếp và nồi cơm điện",
                now - timedelta(hours=6),
                now + timedelta(hours=2),
                TripStatus.DELIVERED.value,
                4,
                4,
                "Đã giao cho anh Hoàng quản lý kho, đã ký biên bản bàn giao",
            ),
        ]

        for (
            ref,
            s_name,
            s_phone,
            p_addr,
            d_addr,
            weight,
            c_type,
            s_time,
            e_time,
            status_val,
            t_id,
            d_id,
            notes,
        ) in trips_data:
            p_time = now - timedelta(hours=5) if status_val in [TripStatus.PICKED_UP.value, TripStatus.IN_TRANSIT.value, TripStatus.DELIVERED.value] else None
            d_time = now - timedelta(hours=4) if status_val in [TripStatus.IN_TRANSIT.value, TripStatus.DELIVERED.value] else None
            deliv_time = now - timedelta(hours=1) if status_val == TripStatus.DELIVERED.value else None
            trip = Trip(
                reference_code=ref,
                sender_name=s_name,
                sender_phone=s_phone,
                pickup_address=p_addr,
                delivery_address=d_addr,
                cargo_weight_kg=weight,
                cargo_type=c_type,
                estimated_start_time=s_time,
                estimated_end_time=e_time,
                status=status_val,
                assigned_truck_id=t_id,
                assigned_driver_id=d_id,
                actual_pickup_time=p_time,
                actual_depart_time=d_time,
                actual_delivery_time=deliv_time,
                recipient_name="Hoàng Quản Lý Kho" if status_val == TripStatus.DELIVERED.value else None,
                notes=notes,
            )
            db.add(trip)
        db.commit()

        # Seed bookings for PKUP, TRNST and DELIV
        b_pkup_truck = ResourceBooking(
            resource_type=ResourceType.TRUCK.value,
            resource_id=2,
            reference_code="TRIP-2026-PKUP",
            service_type=ServiceType.FREIGHT.value,
            start_time=now - timedelta(hours=3),
            end_time=now + timedelta(hours=5),
            status=BookingStatus.IN_PROGRESS.value,
        )
        b_pkup_driver = ResourceBooking(
            resource_type=ResourceType.DRIVER.value,
            resource_id=2,
            reference_code="TRIP-2026-PKUP",
            service_type=ServiceType.FREIGHT.value,
            start_time=now - timedelta(hours=3),
            end_time=now + timedelta(hours=5),
            status=BookingStatus.IN_PROGRESS.value,
        )
        b_trnst_truck = ResourceBooking(
            resource_type=ResourceType.TRUCK.value,
            resource_id=3,
            reference_code="TRIP-2026-TRNST",
            service_type=ServiceType.FREIGHT.value,
            start_time=now - timedelta(hours=5),
            end_time=now + timedelta(hours=8),
            status=BookingStatus.IN_PROGRESS.value,
        )
        b_trnst_driver = ResourceBooking(
            resource_type=ResourceType.DRIVER.value,
            resource_id=3,
            reference_code="TRIP-2026-TRNST",
            service_type=ServiceType.FREIGHT.value,
            start_time=now - timedelta(hours=5),
            end_time=now + timedelta(hours=8),
            status=BookingStatus.IN_PROGRESS.value,
        )
        b_deliv_truck = ResourceBooking(
            resource_type=ResourceType.TRUCK.value,
            resource_id=4,
            reference_code="TRIP-2026-DELIV",
            service_type=ServiceType.FREIGHT.value,
            start_time=now - timedelta(hours=6),
            end_time=now + timedelta(hours=2),
            status=BookingStatus.IN_PROGRESS.value,
        )
        b_deliv_driver = ResourceBooking(
            resource_type=ResourceType.DRIVER.value,
            resource_id=4,
            reference_code="TRIP-2026-DELIV",
            service_type=ServiceType.FREIGHT.value,
            start_time=now - timedelta(hours=6),
            end_time=now + timedelta(hours=2),
            status=BookingStatus.IN_PROGRESS.value,
        )
        db.add_all([b_pkup_truck, b_pkup_driver, b_trnst_truck, b_trnst_driver, b_deliv_truck, b_deliv_driver])
        db.commit()

        # Seed sample evidence for DELIV trip
        deliv_trip = db.query(Trip).filter(Trip.reference_code == "TRIP-2026-DELIV").first()
        if deliv_trip:
            from src.models.trip_evidence import TripEvidence
            sample_evidence = TripEvidence(
                trip_id=deliv_trip.id,
                file_path="uploads/evidence/sample_pod_bien_ban.pdf",
                file_name="bien_ban_ban_giao_sunhouse.pdf",
                file_size_bytes=102400,
                mime_type="application/pdf",
                evidence_type="POD",
                notes="Biên bản giao hàng có đủ chữ ký và dấu đại lý",
                uploaded_by_user_id=1,
            )
            db.add(sample_evidence)
            db.commit()

        # Seed sample issue for TRNST trip (Feature 006: TRN-05)
        trnst_trip = db.query(Trip).filter(Trip.reference_code == "TRIP-2026-TRNST").first()
        if trnst_trip and not trnst_trip.issues:
            from src.models.trip_issue import TripIssue, IssueStatus
            sample_issue = TripIssue(
                trip_id=trnst_trip.id,
                issue_type="VEHICLE_BREAKDOWN",
                description="Xe bị thủng lốp sau trên cao tốc Pháp Vân - Cầu Giẽ, đang chờ đội cứu hộ.",
                occurred_at=now - timedelta(hours=2),
                handled_by="Tài xế Nguyễn Văn A & Cứu hộ cao tốc",
                estimated_resolution_time=now + timedelta(hours=1),
                status=IssueStatus.OPEN.value,
                reported_by_user_id=1,
            )
            db.add(sample_issue)
            db.commit()

        logger.info("Demo trips successfully seeded (8 trips: 4 UNASSIGNED, 1 ASSIGNED, 1 PICKED_UP, 1 IN_TRANSIT, 1 DELIVERED with sample evidence & open issue).")
