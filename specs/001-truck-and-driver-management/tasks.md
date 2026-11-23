# Tasks: TRN-01 Quản lý xe và tài xế

**Input**: Design documents from `specs/001-truck-and-driver-management/`  
**Prerequisites**: [plan.md](file:///d:/PPA.MP08_GROUP3/specs/001-truck-and-driver-management/plan.md), [spec.md](file:///d:/PPA.MP08_GROUP3/specs/001-truck-and-driver-management/spec.md), [research.md](file:///d:/PPA.MP08_GROUP3/specs/001-truck-and-driver-management/research.md), [data-model.md](file:///d:/PPA.MP08_GROUP3/specs/001-truck-and-driver-management/data-model.md), [contracts/](file:///d:/PPA.MP08_GROUP3/specs/001-truck-and-driver-management/contracts/), [quickstart.md](file:///d:/PPA.MP08_GROUP3/specs/001-truck-and-driver-management/quickstart.md)  
**Constitution**: Tuân thủ 5 nguyên tắc trong [.specify/memory/constitution.md](file:///d:/PPA.MP08_GROUP3/.specify/memory/constitution.md)

## Format: `- [X] [ID] [P?] [Story?] Description with file path`
- **[P]**: Có thể thực hiện song song (khác file, không phụ thuộc task chưa hoàn thành)
- **[Story]**: Gán nhãn User Story (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Mô tả kèm đường dẫn file cụ thể và trích dẫn ràng buộc canonical từ `data-model.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Khởi tạo cấu trúc dự án và cài đặt cấu hình cơ sở

- [X] T001 Tạo cấu trúc cây thư mục mã nguồn `src/core`, `src/models`, `src/schemas`, `src/repositories`, `src/services`, `src/api/v1`, `src/web`, `src/templates`, `tests/unit`, `tests/integration` per `plan.md`
- [X] T002 Khởi tạo danh sách dependencies dự án trong `requirements.txt` (FastAPI, Uvicorn, SQLAlchemy, Pydantic v2, Jinja2, pytest, httpx)
- [X] T003 [P] Cấu hình môi trường ứng dụng và database URL trong `src/core/config.py`
- [X] T004 [P] Cấu hình hệ thống logging chuẩn SLF4J / Python Logging trong `src/core/logging.py` (nghiêm cấm dùng print() per Constitution Principle V)
- [X] T005 [P] Xây dựng lớp ngoại lệ miền (Domain Exceptions) và chuẩn hóa cấu trúc phản hồi `ApiResponse` trong `src/core/exceptions.py` và `src/schemas/common.py` per `research.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Hạ tầng lõi và tầng dữ liệu dùng chung (BẮT BUỘC hoàn thành trước khi triển khai các User Story)

⚠️ **CRITICAL**: Không bắt đầu triển khai các User Story trước khi Phase 2 hoàn thành.

- [X] T006 Thiết lập SQLAlchemy engine, SessionLocal factory và Declarative Base trong `src/core/database.py`
- [X] T007 [P] Xây dựng Base Repository pattern hỗ trợ generic CRUD và quản lý session giao dịch trong `src/repositories/base.py`
- [X] T008 [P] Tạo SQLAlchemy model `ResourceBooking` trong `src/models/booking.py` phục vụ kiểm tra lịch trình động và bảo vệ xóa mềm, trích dẫn canonical constraints từ `data-model.md` cho `ResourceBooking.resource_type`, `ResourceBooking.status`, `ResourceBooking.start_time`, `ResourceBooking.end_time`
- [X] T009 Xây dựng `ResourceBookingRepository` trong `src/repositories/booking_repo.py` hỗ trợ truy vấn kiểm tra trùng lặp thời gian và kiểm tra lịch sử booking của nguồn lực
- [X] T010 Thiết lập test fixtures dùng chung và SQLite in-memory database session trong `tests/conftest.py`

**Checkpoint**: Nền tảng cốt lõi sẵn sàng - các User Story có thể bắt đầu triển khai độc lập hoặc song song.

---

## Phase 3: User Story 1 - Quản lý và thiết lập danh mục Xe (Priority: P1) 🎯 MVP

**Goal**: Cho phép tạo mới, cập nhật, tìm kiếm danh mục xe; chuẩn hóa biển số tự động và xác thực tải trọng dương (`capacity_kg > 0`).

**Independent Test**: Chạy `pytest tests/unit/test_trucks.py` - tạo xe `29C-123.45`, xác nhận `normalized_plate` là `29C12345`, kiểm tra từ chối tạo trùng biển số sau chuẩn hóa và từ chối tải trọng `<= 0`.

### Tests for User Story 1 (TDD - Write first) ⚠️
- [X] T011 [P] [US1] Viết unit tests kiểm tra chuẩn hóa biển số, từ chối trùng biển số và validate tải trọng `capacity_kg > 0` trong `tests/unit/test_trucks.py`

### Implementation for User Story 1
- [X] T012 [P] [US1] Tạo SQLAlchemy model `Truck` trong `src/models/truck.py` trích dẫn canonical constraints từ `data-model.md` cho `Truck.normalized_plate` (VARCHAR(20), UNIQUE, INDEX), `Truck.capacity_kg` (CHECK capacity_kg > 0), và `Truck.status` (DEFAULT 'ACTIVE')
- [X] T013 [P] [US1] Tạo Pydantic v2 schemas cho Truck (`CreateTruckRequest`, `UpdateTruckRequest`, `TruckDetailResponse`) trong `src/schemas/truck.py` tuân thủ `contracts/trucks-api.yaml`
- [X] T014 [US1] Hiện thực hóa `TruckRepository` trong `src/repositories/truck_repo.py` với các hàm tra cứu theo normalized_plate, phân trang và tìm kiếm (kế thừa `BaseRepository`)
- [X] T015 [US1] Hiện thực hóa `TruckService` trong `src/services/truck_service.py` tích hợp regex chuẩn hóa biển số (`re.sub`), validate tải trọng dương và kiểm tra trùng lặp
- [X] T016 [US1] Hiện thực hóa REST API endpoints quản lý xe trong `src/api/v1/trucks.py` tuân thủ hợp đồng giao diện `contracts/trucks-api.yaml`
- [X] T017 [US1] Hiện thực hóa web view điều phối viên quản lý xe trong `src/web/admin_trucks.py` cùng Jinja2 templates trong `src/templates/trucks/list.html` và `src/templates/trucks/form.html`

**Checkpoint**: User Story 1 hoàn thành độc lập và kiểm thử pass 100%. Đạt mốc MVP!

---

## Phase 4: User Story 2 - Quản lý và thiết lập danh mục Tài xế (Priority: P1)

**Goal**: Cho phép tạo mới, cập nhật, tìm kiếm danh mục tài xế; đảm bảo mã tài xế duy nhất và số điện thoại liên hệ hợp lệ.

**Independent Test**: Chạy `pytest tests/unit/test_drivers.py` - tạo tài xế mã `TX001`, cập nhật thông tin, kiểm tra từ chối tạo mới khi mã trùng lặp.

### Tests for User Story 2 (TDD - Write first) ⚠️
- [X] T018 [P] [US2] Viết unit tests kiểm tra tính duy nhất của mã tài xế và định dạng số điện thoại trong `tests/unit/test_drivers.py`

### Implementation for User Story 2
- [X] T019 [P] [US2] Tạo SQLAlchemy model `Driver` trong `src/models/driver.py` trích dẫn canonical constraints từ `data-model.md` cho `Driver.driver_code` (VARCHAR(20), UNIQUE, INDEX), `Driver.phone_number` (VARCHAR(20), NOT NULL), và `Driver.status` (DEFAULT 'ACTIVE')
- [X] T020 [P] [US2] Tạo Pydantic v2 schemas cho Driver (`CreateDriverRequest`, `UpdateDriverRequest`, `DriverDetailResponse`) trong `src/schemas/driver.py` tuân thủ `contracts/drivers-api.yaml`
- [X] T021 [US2] Hiện thực hóa `DriverRepository` trong `src/repositories/driver_repo.py` với các hàm tra cứu theo driver_code, phân trang và tìm kiếm
- [X] T022 [US2] Hiện thực hóa `DriverService` trong `src/services/driver_service.py` với nghiệp vụ kiểm tra trùng mã tài xế và định dạng số điện thoại
- [X] T023 [US2] Hiện thực hóa REST API endpoints quản lý tài xế trong `src/api/v1/drivers.py` tuân thủ hợp đồng giao diện `contracts/drivers-api.yaml`
- [X] T024 [US2] Hiện thực hóa web view quản lý tài xế trong `src/web/admin_drivers.py` cùng Jinja2 templates trong `src/templates/drivers/list.html` và `src/templates/drivers/form.html`

**Checkpoint**: User Story 1 và User Story 2 đều hoạt động và kiểm thử độc lập.

---

## Phase 5: User Story 3 - Bảo toàn lịch sử & Khóa xóa cứng (Soft Delete) (Priority: P2)

**Goal**: Đảm bảo xe và tài xế đã phát sinh giao dịch/chuyến hàng không thể bị xóa cứng khỏi CSDL nhằm bảo toàn lịch sử dữ liệu (Immutable Audit Trail).

**Independent Test**: Chạy `pytest tests/integration/test_soft_delete_guard.py` - tạo booking cho xe và tài xế, gọi lệnh xóa, kiểm tra hệ thống từ chối xóa cứng (trả về lỗi HTTP 400 Bad Request) và dữ liệu được bảo toàn.

### Tests for User Story 3 (TDD - Write first) ⚠️
- [X] T025 [P] [US3] Viết integration test trong `tests/integration/test_soft_delete_guard.py` kiểm tra từ chối xóa cứng khi nguồn lực có lịch sử booking trong `ResourceBooking`

### Implementation for User Story 3
- [X] T026 [US3] Hiện thực hóa logic kiểm tra lịch sử trong `src/services/truck_service.py` - chặn gọi hàm xóa cứng khi `booking_repo.has_booking_history()` trả về True, chỉ cho phép đổi trạng thái sang `INACTIVE`
- [X] T027 [US3] Hiện thực hóa logic kiểm tra lịch sử trong `src/services/driver_service.py` - chặn gọi hàm xóa cứng khi tài xế đã có lịch sử booking, chỉ cho phép chuyển sang `INACTIVE`
- [X] T028 [US3] Cập nhật giao diện web và API endpoints trong `src/api/v1/trucks.py`, `src/api/v1/drivers.py`, `src/web/admin_trucks.py`, `src/web/admin_drivers.py` để hiển thị thông báo lỗi rõ ràng khi thao tác xóa bị từ chối

**Checkpoint**: Quy tắc bảo toàn lịch sử dữ liệu (Soft Delete Guard) hoạt động hoàn hảo trên cả 2 thực thể.

---

## Phase 6: User Story 4 - Ràng buộc chuyển trạng thái & Kiểm tra lịch tương lai (Priority: P2)

**Goal**: Ngăn chuyển xe sang `MAINTENANCE`/`INACTIVE` hoặc tài xế sang `INACTIVE` nếu còn lịch phân công trong tương lai; cấm chuyển sang `INACTIVE` khi đang trong chuyến (`IN_PROGRESS`).

**Independent Test**: Chạy `pytest tests/integration/test_truck_lifecycle.py` - tạo booking tương lai cho xe ID 1, gửi request đổi trạng thái sang `MAINTENANCE`, kiểm tra hệ thống trả về mã 409 Conflict kèm danh sách booking xung đột.

### Tests for User Story 4 (TDD - Write first) ⚠️
- [X] T029 [P] [US4] Viết integration test trong `tests/integration/test_truck_lifecycle.py` kiểm tra ràng buộc chuyển trạng thái và phát hiện xung đột lịch tương lai

### Implementation for User Story 4
- [X] T030 [US4] Hiện thực hóa phương thức kiểm tra lịch tương lai và trạng thái đang chạy trong `src/services/truck_service.py`, trích dẫn state transitions từ `data-model.md` cho `Truck.status`
- [X] T031 [US4] Hiện thực hóa phương thức kiểm tra lịch tương lai trong `src/services/driver_service.py`, trích dẫn state transitions từ `data-model.md` cho `Driver.status`
- [X] T032 [US4] Cập nhật endpoint `PATCH /api/v1/trucks/{id}/status` và `PATCH /api/v1/drivers/{id}/status` trong `src/api/v1/trucks.py` và `src/api/v1/drivers.py` trả về `ScheduleConflictResponse` (HTTP 409 Conflict) khi phát hiện lịch xung đột tuân thủ contracts
- [X] T033 [US4] Bổ sung modal cảnh báo xung đột lịch và bảng liệt kê booking tương lai trên giao diện web `src/templates/trucks/list.html` và `src/templates/drivers/list.html`

**Checkpoint**: Toàn bộ 4 User Stories đã được tích hợp đầy đủ, độc lập và bảo vệ chặt chẽ các ràng buộc nghiệp vụ.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Tích hợp toàn diện, chuẩn hóa giao diện và nghiệm thu hệ thống

- [X] T034 [P] Xây dựng file khởi tạo ứng dụng chính `src/main.py` đăng ký toàn bộ routers (`/api/v1`, `/admin`), exception handlers tập trung và cấu hình static/templates
- [X] T035 [P] Xây dựng template giao diện cơ sở `src/templates/base.html` với Bootstrap 5, navbar điều hướng hệ thống vận tải và thông báo flash message
- [X] T036 Thực thi toàn bộ bộ kiểm thử tự động `pytest tests/ -v` và kiểm tra 5 kịch bản nghiệm thu trong `quickstart.md` đạt 100% PASS

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)**: Có thể thực hiện ngay lập tức.
- **Phase 2 (Foundational)**: Phụ thuộc vào Phase 1; KHÓA (BLOCK) toàn bộ các User Story.
- **Phase 3 (User Story 1 - Xe)**: Bắt đầu ngay sau khi Phase 2 hoàn thành.
- **Phase 4 (User Story 2 - Tài xế)**: Bắt đầu sau Phase 2; có thể chạy song song với User Story 1.
- **Phase 5 (User Story 3 - Soft Delete)**: Phụ thuộc vào models/services của US1 và US2.
- **Phase 6 (User Story 4 - Lịch tương lai)**: Phụ thuộc vào models/services của US1 và US2.
- **Phase 7 (Polish)**: Chạy khi tất cả các User Stories hoàn tất.

### Parallel Opportunities
- Các task Setup [P] (T003, T004, T005) có thể triển khai song song.
- Trong Phase 2, T007 và T008 có thể làm song song.
- Sau Phase 2, User Story 1 (T011-T017) và User Story 2 (T018-T024) có thể được lập trình viên triển khai độc lập song song mà không xung đột file.
- Trong từng User Story, task viết Test [P] được viết trước theo TDD.

---

## Implementation Strategy

### MVP First (User Story 1 - Quản lý xe)
1. Hoàn thành Phase 1: Setup
2. Hoàn thành Phase 2: Foundational (Bắt buộc)
3. Hoàn thành Phase 3: User Story 1
4. **Dừng & Nghiệm thu MVP**: Chạy `pytest tests/unit/test_trucks.py` kiểm tra trọn vẹn nghiệp vụ quản lý xe.

### Incremental Delivery (Giao hàng theo từng chặng)
1. Setup + Foundational ➔ Sẵn sàng hạ tầng
2. Thêm US1 (Xe) ➔ Nghiệm thu MVP ➔ Triển khai demo
3. Thêm US2 (Tài xế) ➔ Nghiệm thu quản lý tài nguyên hoàn chỉnh
4. Thêm US3 (Khóa xóa cứng) + US4 (Ràng buộc lịch tương lai) ➔ Nghiệm thu toàn vẹn dữ liệu và an toàn vận hành
5. Tích hợp giao diện web Bootstrap 5 và kiểm thử toàn hệ thống per `quickstart.md`.
