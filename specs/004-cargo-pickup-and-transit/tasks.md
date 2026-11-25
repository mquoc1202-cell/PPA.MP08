# Tasks: TRN-03 Ghi nhận nhận hàng và vận chuyển (Cargo Pickup & In-Transit Tracking)

**Input**: Design documents from `specs/004-cargo-pickup-and-transit/`  
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/pickup-api.yaml](contracts/pickup-api.yaml), [quickstart.md](quickstart.md)  
**Constitution**: Tuân thủ nghiêm ngặt 5 nguyên tắc trong [.specify/memory/constitution.md](../../.specify/memory/constitution.md)

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`
- **[P]**: Có thể chạy song song (khác file, không phụ thuộc task chưa xong)
- **[Story]**: Gán nhãn User Story (`[US1]`, `[US2]`, `[US3]`, `[US4]`, `[US5]`)
- Mô tả kèm đường dẫn file cụ thể và trích dẫn ràng buộc canonical từ `data-model.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Mở rộng cấu trúc model Chuyến hàng và khởi tạo thực thể sự kiện dòng thời gian

- [X] T001 Mở rộng model `Trip` trong `src/models/trip.py` bổ sung các cột theo dõi mốc trích dẫn canonical constraints từ `data-model.md` cho `Trip.actual_cargo_weight_kg` (INTEGER, NULLABLE, CHECK actual_cargo_weight_kg > 0), `Trip.handover_person` (VARCHAR(100), NULLABLE), `Trip.cargo_condition` (VARCHAR(255), NULLABLE), `Trip.discrepancy_notes` (VARCHAR(500), NULLABLE), `Trip.actual_pickup_time` (DATETIME, NULLABLE), `Trip.actual_depart_time` (DATETIME, NULLABLE), `Trip.pickup_recorded_at` (DATETIME, NULLABLE), và `Trip.depart_recorded_at` (DATETIME, NULLABLE)
- [X] T002 [P] Tạo SQLAlchemy model `TripEvent` trong `src/models/trip_event.py` trích dẫn canonical constraints từ `data-model.md` cho `TripEvent.trip_id` (INTEGER, NOT NULL, FOREIGN KEY trips.id ON DELETE CASCADE, INDEX), `TripEvent.event_type` (VARCHAR(50), NOT NULL), `TripEvent.from_status` (VARCHAR(20), NOT NULL), `TripEvent.to_status` (VARCHAR(20), NOT NULL), `TripEvent.actual_time` (DATETIME, NOT NULL), `TripEvent.recorded_at` (DATETIME, NOT NULL, DEFAULT UTC NOW), và `TripEvent.recorded_by_user_id` (FOREIGN KEY users.id). Cập nhật `src/models/__init__.py`.
- [X] T003 [P] Tạo Pydantic v2 schemas cho Pickup, Departure & Timeline (`RecordPickupRequest`, `RecordDepartureRequest`, `TripEventItem`, `TripEventsResponse`) trong `src/schemas/trip.py` tuân thủ `contracts/pickup-api.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Xây dựng tầng Data Access Layer cho sự kiện và nâng cấp repository lịch trình

⚠️ **CRITICAL**: Không bắt đầu triển khai các User Story trước khi Phase 2 hoàn thành.

- [X] T004 Xây dựng `TripEventRepository` trong `src/repositories/trip_event_repo.py` hỗ trợ ghi nhận sự kiện mốc bất biến và truy vấn danh sách sự kiện theo `trip_id` sắp xếp theo thời gian
- [X] T005 [P] Nâng cấp `ResourceBookingRepository` trong `src/repositories/booking_repo.py` bổ sung phương thức `transition_bookings_status` (chuyển trạng thái booking từ `CONFIRMED` sang `IN_PROGRESS`) và `has_in_progress_booking` (kiểm tra xe hoặc tài xế có đang dở dang chuyến khác theo quy tắc BR-09)
- [X] T006 Nạp dữ liệu mẫu Chuyến hàng (`Trip`) và Sự kiện (`TripEvent`) trong `src/core/seed.py` với các chuyến ở trạng thái `PICKED_UP` và `IN_TRANSIT` phục vụ kiểm thử

**Checkpoint**: Nền tảng dữ liệu và Repository sẵn sàng - các User Story bắt đầu triển khai.

---

## Phase 3: User Story 1 - Ghi nhận Nhận hàng Thực tế tại Điểm lấy hàng (Priority: P1) 🎯 MVP

**Goal**: Cho phép điều phối viên ghi nhận nhận hàng thực tế cho chuyến hàng `ASSIGNED`, lưu người bàn giao, tình trạng hàng, chuyển trạng thái chuyến sang `PICKED_UP` và tự động chuyển booking của xe/tài xế sang `IN_PROGRESS`.

**Independent Test**: Chạy `pytest tests/unit/test_pickup.py` - kiểm tra nhận hàng hợp lệ thành công (chuyến sang `PICKED_UP`, 2 booking sang `IN_PROGRESS`, ghi nhận sự kiện vào `trip_events`), và từ chối nếu chuyến không ở trạng thái `ASSIGNED`.

### Tests for User Story 1 (TDD - Write first) ⚠️
- [X] T007 [P] [US1] Viết unit tests trong `tests/unit/test_pickup.py` kiểm tra nhận hàng thành công từ `ASSIGNED` sang `PICKED_UP`, đồng bộ booking sang `IN_PROGRESS`, và từ chối khi chuyến ở các trạng thái khác (`UNASSIGNED`, `PICKED_UP`, `DELIVERED`)
- [X] T008 [P] [US1] Viết contract test cho endpoint `POST /api/v1/trips/{id}/pickup` trong `tests/contract/test_pickup_api.py`

### Implementation for User Story 1
- [X] T009 [US1] Hiện thực hóa phương thức `record_pickup` trong `src/services/trip_tracking_service.py` đảm bảo cập nhật trạng thái chuyến, lưu thời điểm thực tế, thời điểm hệ thống, gọi `TripEventRepository` tạo sự kiện, và đồng bộ booking sang `IN_PROGRESS` trong một Atomic Transaction
- [X] T010 [US1] Hiện thực hóa REST API endpoint `POST /api/v1/trips/{id}/pickup` trong `src/api/v1/trips.py` áp dụng bảo vệ `require_role(["DSP"])`
- [X] T011 [US1] Hiện thực hóa Web controller `GET /trips/{id}/pickup` và `POST /trips/{id}/pickup` trong `src/web/trips.py`
- [X] T012 [US1] Xây dựng giao diện ghi nhận nhận hàng `src/templates/trips/pickup.html` theo `frontend/DESIGN.md` có đầy đủ các trường người bàn giao, tình trạng bao bì, khối lượng thực tế và thời điểm nhận

**Checkpoint**: User Story 1 hoàn thành độc lập và kiểm thử pass 100%. Đạt mốc MVP!

---

## Phase 4: User Story 2 - Kiểm tra & Từ chối Vượt Tải trọng Thực tế tại Điểm lấy hàng (Priority: P1)

**Goal**: Tự động kiểm tra khối lượng hàng thực tế cân được tại kho so với tải trọng cho phép của xe; nếu quá tải (`actual_cargo_weight_kg > truck.capacity_kg`), từ chối xác nhận nhận hàng và giữ nguyên chuyến ở `ASSIGNED`.

**Independent Test**: Chạy `pytest tests/unit/test_pickup.py` - kiểm tra trường hợp khối lượng thực tế 5,200 kg vượt quá tải trọng xe 5,000 kg bị ném ngoại lệ 400, chuyến vẫn là `ASSIGNED` và booking vẫn ở `CONFIRMED`.

### Tests for User Story 2 (TDD - Write first) ⚠️
- [X] T013 [P] [US2] Viết unit test kiểm tra từ chối nhận hàng do quá tải thực tế trong `tests/unit/test_pickup.py` và chấp nhận khi khối lượng $\le$ tải trọng xe

### Implementation for User Story 2
- [X] T014 [US2] Tích hợp logic kiểm tra tải trọng thực tế trong phương thức `record_pickup` tại `src/services/trip_tracking_service.py` ném ngoại lệ `BusinessRuleViolationError` khi quá tải
- [X] T015 [US2] Bổ sung mã JavaScript kiểm tra tải trọng thời gian thực trên form `src/templates/trips/pickup.html` hiển thị viền đỏ cảnh báo và vô hiệu hóa nút xác nhận khi vượt tải

---

## Phase 5: User Story 3 - Kiểm tra Xung đột Thực thi Nguồn lực theo Quy tắc BR-09 (Priority: P2)

**Goal**: Ngăn chặn nhận hàng nếu xe tải hoặc tài xế được phân công đang dở dang thực hiện một chuyến khác có booking ở trạng thái `IN_PROGRESS`.

**Independent Test**: Chạy `pytest tests/integration/test_trip_transitions.py` - tạo Chuyến 1 đang `IN_PROGRESS` với Xe A/Tài xế B; kiểm tra xác nhận nhận hàng cho Chuyến 2 cùng nguồn lực bị từ chối với lỗi BR-09.

### Tests for User Story 3 (TDD - Write first) ⚠️
- [X] T016 [P] [US3] Viết integration test mô phỏng kịch bản tài nguyên đang bận thực hiện chuyến khác theo quy tắc BR-09 trong `tests/integration/test_trip_transitions.py`

### Implementation for User Story 3
- [X] T017 [US3] Tích hợp kiểm tra `has_in_progress_booking` trong phương thức `record_pickup` tại `src/services/trip_tracking_service.py` ném ngoại lệ `ScheduleConflictError` nếu tài nguyên đang dở dang nhiệm vụ khác

---

## Phase 6: User Story 4 - Ghi nhận Khởi hành và Chuyển trạng thái Đang vận chuyển (`IN_TRANSIT`) (Priority: P2)

**Goal**: Cho phép điều phối viên ghi nhận xe rời điểm lấy hàng, cập nhật thời điểm xuất phát thực tế, chuyển trạng thái chuyến từ `PICKED_UP` sang `IN_TRANSIT` và chặn mọi hành vi nhảy cóc trạng thái.

**Independent Test**: Chạy `pytest tests/unit/test_pickup.py` - chuyến `PICKED_UP` chuyển thành công sang `IN_TRANSIT`; chặn chuyển sang `IN_TRANSIT` nếu chuyến đang ở `ASSIGNED` hoặc `UNASSIGNED`; chặn nếu thời điểm khởi hành trước thời điểm nhận hàng.

### Tests for User Story 4 (TDD - Write first) ⚠️
- [X] T018 [P] [US4] Viết unit tests trong `tests/unit/test_pickup.py` kiểm tra ghi nhận khởi hành hợp lệ, chặn nhảy cóc trạng thái, và chặn thời gian khởi hành trước thời gian nhận hàng

### Implementation for User Story 4
- [X] T019 [US4] Hiện thực hóa phương thức `record_departure` trong `src/services/trip_tracking_service.py` kiểm tra trạng thái `PICKED_UP`, cập nhật `actual_depart_time`, chuyển trạng thái `IN_TRANSIT`, và tạo bản ghi sự kiện `TripEvent`
- [X] T020 [US4] Hiện thực hóa REST API endpoint `POST /api/v1/trips/{id}/depart` trong `src/api/v1/trips.py` áp dụng bảo vệ `require_role(["DSP"])`
- [X] T021 [US4] Bổ sung Web action xử lý khởi hành trong `src/web/trips.py` và cập nhật nút bấm thao tác trên `src/templates/trips/list.html`

---

## Phase 7: User Story 5 - Dòng thời gian Lịch sử & Phân quyền Tra cứu Tiến độ (Priority: P3)

**Goal**: Cung cấp giao diện hiển thị chi tiết chuyến hàng và dòng thời gian các mốc sự kiện (Timeline); bảo vệ phân quyền hiển thị và chặn thao tác ghi từ người dùng vai trò `SAL` hoặc `MGR`.

**Independent Test**: Chạy `pytest tests/integration/test_trip_transitions.py` - kiểm tra tài khoản `sal` xem được dòng thời gian đầy đủ nhưng nhận mã lỗi 403 Forbidden khi cố gắng gửi yêu cầu nhận hàng hoặc khởi hành.

### Tests for User Story 5 (TDD - Write first) ⚠️
- [X] T022 [P] [US5] Viết integration test trong `tests/integration/test_trip_transitions.py` kiểm tra truy vấn dòng thời gian `TripEvent` và phân quyền RBAC (DSP cho phép, SAL/MGR chặn 403 khi ghi)

### Implementation for User Story 5
- [X] T023 [US5] Hiện thực hóa REST API endpoint `GET /api/v1/trips/{id}/events` trong `src/api/v1/trips.py` trả về danh sách sự kiện dòng thời gian
- [X] T024 [US5] Xây dựng màn hình chi tiết chuyến hàng `src/templates/trips/detail.html` hiển thị khối thông tin tổng hợp và Vertical Timeline các mốc sự kiện theo `frontend/DESIGN.md`

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Tích hợp toàn diện vào ứng dụng, tự động hóa cập nhật schema cơ sở dữ liệu và nghiệm thu chất lượng

- [X] T025 [P] Cập nhật danh sách chuyến hàng `src/templates/trips/list.html` bổ sung liên kết xem chi tiết (`/trips/{id}`) và huy hiệu trạng thái `PICKED_UP`, `IN_TRANSIT`
- [X] T026 Tự động kiểm tra và thêm các cột mới cho `trips` cũng như tạo bảng `trip_events` nếu thiếu trong hàm `lifespan` tại `src/main.py`
- [X] T027 Thực thi toàn bộ bộ kiểm thử tự động `pytest tests/ -v` xác nhận 100% test cases (cả TRN-01, Auth, TRN-02, và TRN-03) đạt trạng thái PASS

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)**: Mở rộng `Trip`, tạo `TripEvent` và Pydantic schemas.
- **Phase 2 (Foundational)**: Xây dựng Repositories, nạp seed data mẫu ➔ KHÓA (BLOCK) toàn bộ các User Story.
- **Phase 3 (User Story 1 - Nhận hàng MVP)**: Triển khai phương thức `record_pickup` và màn hình nhận hàng.
- **Phase 4 (User Story 2 - Chặn quá tải)**: Tích hợp trực tiếp vào quy trình nhận hàng của User Story 1.
- **Phase 5 (User Story 3 - Kiểm tra BR-09)**: Củng cố kiểm tra xung đột thực thi nguồn lực.
- **Phase 6 (User Story 4 - Khởi hành IN_TRANSIT)**: Kế thừa từ trạng thái `PICKED_UP`.
- **Phase 7 (User Story 5 - Timeline & Phân quyền)**: Trực quan hóa toàn bộ dòng thời gian và áp dụng RBAC.
- **Phase 8 (Polish)**: Nghiệm thu toàn diện test suite.

### Parallel Opportunities
- T001, T002, T003 có thể làm song song trong Phase 1.
- T004 và T005 có thể làm song song trong Phase 2.
- T007 và T008 (viết tests US1) có thể làm song song.
- T013, T016, T018, T022 (viết tests cho US2, US3, US4, US5) có thể làm song song.
- T025 và T026 có thể làm song song trong Phase 8.

---

## Implementation Strategy

### MVP First (User Story 1 - Actual Pickup)
1. Hoàn thành Setup + Foundational.
2. Hoàn thành User Story 1 (Ghi nhận nhận hàng, chuyển chuyến sang `PICKED_UP`, chuyển booking sang `IN_PROGRESS`).
3. **Nghiệm thu MVP**: Điều phối viên xác nhận nhận hàng thành công một đơn hàng trên hệ thống.

### Incremental Delivery
1. Setup + Foundational ➔ Sẵn sàng Model `TripEvent` và mở rộng `Trip`.
2. Thêm US1 (Nhận hàng MVP) ➔ Chuyến hàng chuyển trạng thái sang `PICKED_UP`.
3. Thêm US2 (Chặn quá tải) ➔ Tự động từ chối nếu khối lượng thực tế vượt tải trọng xe.
4. Thêm US3 (Quy tắc BR-09) ➔ Chặn nhận hàng nếu xe/tài xế đang bận chuyến khác.
5. Thêm US4 (Khởi hành) ➔ Chuyến chuyển sang `IN_TRANSIT`, chặn nhảy cóc trạng thái.
6. Thêm US5 (Dòng thời gian Timeline) ➔ Xem lịch sử các mốc và phân quyền tra cứu.
7. Nghiệm thu toàn diện 100% test suite.
