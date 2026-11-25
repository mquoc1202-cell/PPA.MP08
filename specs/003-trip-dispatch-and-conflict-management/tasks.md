# Tasks: 003-trip-dispatch-and-conflict-management

**Input**: Design documents from `specs/003-trip-dispatch-and-conflict-management/`  
**Prerequisites**: [plan.md](file:///d:/PPA.MP08_GROUP3/specs/003-trip-dispatch-and-conflict-management/plan.md), [spec.md](file:///d:/PPA.MP08_GROUP3/specs/003-trip-dispatch-and-conflict-management/spec.md), [research.md](file:///d:/PPA.MP08_GROUP3/specs/003-trip-dispatch-and-conflict-management/research.md), [data-model.md](file:///d:/PPA.MP08_GROUP3/specs/003-trip-dispatch-and-conflict-management/data-model.md), [contracts/](file:///d:/PPA.MP08_GROUP3/specs/003-trip-dispatch-and-conflict-management/contracts/), [quickstart.md](file:///d:/PPA.MP08_GROUP3/specs/003-trip-dispatch-and-conflict-management/quickstart.md)  
**Constitution**: Tuân thủ nghiêm ngặt 5 nguyên tắc trong [.specify/memory/constitution.md](file:///d:/PPA.MP08_GROUP3/.specify/memory/constitution.md)

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`
- **[P]**: Có thể chạy song song (khác file, không phụ thuộc task chưa xong)
- **[Story]**: Gán nhãn User Story (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Mô tả kèm đường dẫn file cụ thể và trích dẫn ràng buộc canonical từ `data-model.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Mở rộng thực thể booking hỗ trợ đa loại dịch vụ và xây dựng Pydantic schemas

- [X] T001 Cập nhật model `ResourceBooking` trong `src/models/booking.py` bổ sung cột `service_type` trích dẫn canonical constraints từ `data-model.md` cho `ResourceBooking.service_type` (VARCHAR(20), NOT NULL, DEFAULT 'FREIGHT', CHECK service_type IN ('FREIGHT', 'RENTAL'))
- [X] T002 [P] Tạo Pydantic v2 schemas cho Trip & Dispatch (`CreateTripRequest`, `AssignTripRequest`, `ReassignTripRequest`, `TripItem`, `TripDetailResponse`, `TripListResponse`, `ScheduleListResponse`, `ConflictResponse`) trong `src/schemas/trip.py` tuân thủ `contracts/trips-api.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Khởi tạo cấu trúc bảng Chuyến hàng và tầng Repository điều phối dữ liệu

⚠️ **CRITICAL**: Không bắt đầu triển khai các User Story trước khi Phase 2 hoàn thành.

- [X] T003 Tạo SQLAlchemy model `Trip` và enum `TripStatus` trong `src/models/trip.py` trích dẫn canonical constraints từ `data-model.md` cho `Trip.reference_code` (VARCHAR(50), UNIQUE, INDEX), `Trip.cargo_weight_kg` (INTEGER, NOT NULL, CHECK cargo_weight_kg > 0), `Trip.status` (VARCHAR(20), NOT NULL, DEFAULT 'UNASSIGNED', CHECK status IN ('UNASSIGNED', 'ASSIGNED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED', 'CANCELLED')), `Trip.assigned_truck_id` (FOREIGN KEY trucks.id), và `Trip.assigned_driver_id` (FOREIGN KEY drivers.id). Cập nhật `src/models/__init__.py`.
- [X] T004 [P] Xây dựng `TripRepository` trong `src/repositories/trip_repo.py` hỗ trợ tìm kiếm, lọc theo trạng thái, tra cứu theo ID và mã chuyến
- [X] T005 [P] Nâng cấp `ResourceBookingRepository` trong `src/repositories/booking_repo.py` hỗ trợ tham số `exclude_reference_code` khi kiểm tra trùng lịch và tra cứu theo khoảng ngày
- [X] T006 Nạp dữ liệu mẫu Chuyến hàng (`Trip`) trong `src/core/seed.py` với các đơn hàng thực tế ở trạng thái `UNASSIGNED` và `ASSIGNED` phục vụ kiểm thử

**Checkpoint**: Nền tảng dữ liệu Chuyến hàng sẵn sàng - các User Story bắt đầu triển khai.

---

## Phase 3: User Story 1 - Phân công Xe và Tài xế cho Chuyến hàng mới (Priority: P1) 🎯 MVP

**Goal**: Cho phép điều phối viên phân công xe tải và tài xế phù hợp cho chuyến hàng `UNASSIGNED`, kiểm tra tải trọng, tính sẵn sàng và trùng lịch, chuyển trạng thái sang `ASSIGNED` và tạo booking nguyên tử.

**Independent Test**: Chạy `pytest tests/unit/test_dispatch.py` - kiểm tra phân công hợp lệ thành công (tạo 2 booking), từ chối quá tải trọng (BR-06), từ chối xe/tài xế không ACTIVE, và từ chối trùng lịch (BR-07, BR-08) mà không sinh booking một phần.

### Tests for User Story 1 (TDD - Write first) ⚠️
- [X] T007 [P] [US1] Viết unit tests trong `tests/unit/test_dispatch.py` kiểm tra các kịch bản phân công thành công, từ chối quá tải trọng, từ chối xe bảo dưỡng, và từ chối trùng lịch
- [X] T008 [P] [US1] Viết contract test cho các endpoint `GET /api/v1/trips` và `POST /api/v1/trips/{id}/assign` trong `tests/contract/test_trips_api.py`

### Implementation for User Story 1
- [X] T009 [US1] Hiện thực hóa phương thức `assign_trip` trong `src/services/dispatch_service.py` đảm bảo giao dịch nguyên tử (Atomic Transaction), kiểm tra tải trọng (`capacity_kg >= cargo_weight_kg`), trạng thái `ACTIVE`, kiểm tra trùng lịch và tạo 2 `ResourceBooking`
- [X] T010 [US1] Hiện thực hóa REST API endpoints `GET /api/v1/trips`, `POST /api/v1/trips`, `GET /api/v1/trips/{id}`, và `POST /api/v1/trips/{id}/assign` trong `src/api/v1/trips.py` áp dụng bảo vệ `require_role(["DSP"])`
- [X] T011 [US1] Hiện thực hóa Web controller `GET /trips`, `GET /trips/{id}/dispatch`, và `POST /trips/{id}/dispatch` trong `src/web/trips.py`
- [X] T012 [US1] Xây dựng giao diện danh sách chuyến hàng `src/templates/trips/list.html` và màn hình điều phối `src/templates/trips/dispatch.html` có cảnh báo trực quan tải trọng theo `frontend/DESIGN.md`

**Checkpoint**: User Story 1 hoàn thành độc lập và kiểm thử pass 100%. Đạt mốc MVP!

---

## Phase 4: User Story 2 - Thay đổi hoặc Hủy Phân công Nguồn lực trước khi Nhận hàng (Priority: P2)

**Goal**: Cho phép điều phối viên đổi xe, đổi tài xế hoặc hủy phân công đưa chuyến về `UNASSIGNED` khi ở trạng thái `ASSIGNED`, tự động giải phóng lịch cũ; khóa chặt mọi can thiệp phân công khi chuyến đã sang `PICKED_UP`.

**Independent Test**: Chạy `pytest tests/integration/test_dispatch_lifecycle.py` - đổi xe thành công giải phóng booking cũ; đổi thất bại giữ nguyên phân công cũ; gỡ phân công đưa chuyến về `UNASSIGNED`; gọi lệnh đổi trên chuyến `PICKED_UP` bị trả mã HTTP 400.

### Tests for User Story 2 (TDD - Write first) ⚠️
- [X] T013 [P] [US2] Viết integration tests trong `tests/integration/test_dispatch_lifecycle.py` kiểm tra đổi phân công hợp lệ, đổi thất bại giữ nguyên trạng thái, gỡ phân công, và khóa can thiệp khi đã nhận hàng `PICKED_UP`

### Implementation for User Story 2
- [X] T014 [US2] Hiện thực hóa phương thức `reassign_trip` và `unassign_trip` trong `src/services/dispatch_service.py` kiểm tra điều kiện trạng thái `ASSIGNED` và giải phóng booking an toàn
- [X] T015 [US2] Hiện thực hóa REST API endpoints `POST /api/v1/trips/{id}/reassign` và `POST /api/v1/trips/{id}/unassign` trong `src/api/v1/trips.py`
- [X] T016 [US2] Bổ sung Web action xử lý đổi phân công và hủy phân công trong `src/web/trips.py` kèm Modal xác nhận hủy an toàn

**Checkpoint**: User Story 1 và User Story 2 hoàn tất trọn vẹn vòng đời phân công và điều chỉnh nguồn lực.

---

## Phase 5: User Story 3 - Kiểm soát Xung đột Đồng thời (Concurrency Lock) (Priority: P2)

**Goal**: Bảo vệ hệ thống khỏi race condition khi 2 điều phối viên cùng lúc gán 1 xe hoặc tài xế vào khung giờ chồng lấn; đảm bảo chỉ 1 người thành công và người còn lại nhận thông báo lỗi HTTP 409 Conflict.

**Independent Test**: Chạy `pytest tests/integration/test_dispatch_concurrency.py` - mô phỏng 2 tiến trình phân công đồng thời cùng 1 xe, xác nhận 1 tiến trình 200/201 và 1 tiến trình nhận 409 Conflict.

### Tests for User Story 3 (TDD - Write first) ⚠️
- [X] T017 [P] [US3] Viết integration test mô phỏng tranh chấp đồng thời giữa 2 điều phối viên trên cùng một nguồn lực trong `tests/integration/test_dispatch_concurrency.py`

### Implementation for User Story 3
- [X] T018 [US3] Hiện thực hóa cơ chế Transaction Isolation & Concurrency Locking trong `src/services/dispatch_service.py` đảm bảo phát hiện xung đột tức thì khi có giao dịch đồng thời
- [X] T019 [US3] Xây dựng Modal cảnh báo xung đột lịch trình chi tiết (HTTP 409) trên giao diện `src/templates/trips/dispatch.html` hiển thị mã đơn và khung giờ bị chiếm dụng

**Checkpoint**: Toàn bộ nghiệp vụ phân công được bảo vệ chống tranh chấp đồng thời tuyệt đối.

---

## Phase 6: User Story 4 - Tra cứu Lịch trình Chiếm dụng Nguồn lực (Priority: P3)

**Goal**: Cung cấp giao diện và API tra cứu danh sách lịch chiếm dụng của từng xe và tài xế theo ngày hoặc khoảng ngày.

**Independent Test**: Chạy `pytest tests/unit/test_schedule.py` - kiểm tra API và màn hình tra cứu trả về đúng danh sách các booking trong khoảng ngày được chọn.

### Tests for User Story 4 (TDD - Write first) ⚠️
- [X] T020 [P] [US4] Viết test kiểm tra truy vấn lịch chiếm dụng theo ngày và khoảng ngày trong `tests/unit/test_schedule.py`

### Implementation for User Story 4
- [X] T021 [US4] Hiện thực hóa REST API endpoints `GET /api/v1/schedule/trucks/{id}` và `GET /api/v1/schedule/drivers/{id}` trong `src/api/v1/schedule.py`
- [X] T022 [US4] Hiện thực hóa Web controller `GET /schedule` trong `src/web/schedule.py` và template `src/templates/schedule/index.html` hiển thị danh sách lịch chiếm dụng

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Tích hợp toàn diện vào ứng dụng, điều hướng thanh menu và nghiệm thu chất lượng

- [X] T023 [P] Cập nhật Top Navigation Bar trong `src/templates/base.html` bổ sung menu điều hướng `Chuyến Hàng` (`/trips`) và `Lịch Trình` (`/schedule`)
- [X] T024 [P] Đăng ký trips router và schedule router vào `src/main.py` và `src/api/v1/api_router.py`
- [X] T025 Thực thi toàn bộ bộ kiểm thử tự động `pytest tests/ -v` xác nhận 100% test cases (cả TRN-01, Auth, và TRN-02) đạt trạng thái PASS

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)**: Thực hiện trước tiên để mở rộng `ResourceBooking` và định nghĩa schemas.
- **Phase 2 (Foundational)**: Phụ thuộc vào Phase 1; KHÓA (BLOCK) toàn bộ các User Story.
- **Phase 3 (User Story 1 - Phân công MVP)**: Bắt đầu ngay sau khi Phase 2 hoàn thành.
- **Phase 4 (User Story 2 - Đổi/Gỡ phân công)**: Kế thừa từ User Story 1.
- **Phase 5 (User Story 3 - Concurrency Lock)**: Củng cố tính bền vững cho Service phân công.
- **Phase 6 (User Story 4 - Tra cứu lịch)**: Sử dụng lại tầng Repository lịch trình.
- **Phase 7 (Polish)**: Nghiệm thu toàn diện test suite.

### Parallel Opportunities
- T001 và T002 có thể làm song song trong Phase 1.
- T004 và T005 có thể làm song song trong Phase 2.
- T007 và T008 (viết tests US1) có thể chuẩn bị song song.
- T013, T017, T020 (viết tests cho US2, US3, US4) có thể chuẩn bị song song.
- T023 và T024 có thể làm song song trong Phase 7.

---

## Implementation Strategy

### MVP First (User Story 1 - Dispatching)
1. Hoàn thành Setup + Foundational.
2. Hoàn thành User Story 1 (Phân công xe/tài xế + kiểm tra tải trọng + trùng lịch + atomic booking).
3. **Nghiệm thu MVP**: Điều phối viên gán thành công chuyến hàng sang `ASSIGNED`.

### Incremental Delivery
1. Setup + Foundational ➔ Sẵn sàng Model `Trip` và bảng `ResourceBooking`.
2. Thêm US1 (Phân công) ➔ Đơn hàng được gán nguồn lực và tạo booking (MVP!).
3. Thêm US2 (Đổi/Gỡ phân công) ➔ Linh hoạt điều chỉnh trước khi nhận hàng.
4. Thêm US3 (Khóa đồng thời) ➔ Bảo vệ chống xung đột giữa 2 điều phối viên.
5. Thêm US4 (Tra cứu lịch) ➔ Trực quan hóa kế hoạch sử dụng xe/tài xế.
6. Nghiệm thu toàn diện 100% test suite.

