# Tasks: TRN-05 Quản lý sự cố và chậm tiến độ (Incident & Delay Management)

**Input**: Design documents from `specs/006-incident-and-delay-management/`  
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/incident-api.yaml](contracts/incident-api.yaml), [quickstart.md](quickstart.md)  
**Constitution**: Tuân thủ nghiêm ngặt 5 nguyên tắc trong [.specify/memory/constitution.md](../../.specify/memory/constitution.md)

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`
- **[P]**: Có thể chạy song song (khác file, không phụ thuộc task chưa xong)
- **[Story]**: Gán nhãn User Story (`[US1]`, `[US2]`, `[US3]`, `[US4]`, `[US5]`)
- Mô tả kèm đường dẫn file cụ thể và trích dẫn ràng buộc canonical từ `data-model.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Mở rộng cấu trúc thực thể Sự cố, Chuyến hàng, Dòng thời gian và Pydantic schemas

- [X] T001 Mở rộng model `TripIssue` trong `src/models/trip_issue.py` bổ sung các cột trích dẫn canonical constraints từ `data-model.md` cho `TripIssue.occurred_at` (DATETIME, NOT NULL, DEFAULT UTC NOW), `TripIssue.handled_by` (VARCHAR(150), NULLABLE), `TripIssue.estimated_resolution_time` (DATETIME, NULLABLE), `TripIssue.resolution_notes` (VARCHAR(1000), NULLABLE), và `TripIssue.resolved_at` (DATETIME, NULLABLE)
- [X] T002 [P] Mở rộng model `Trip` trong `src/models/trip.py` bổ sung các thuộc tính tính toán trích dẫn canonical constraints từ `data-model.md` cho `Trip.is_delayed` (boolean property: `current_time > estimated_end_time` khi chuyến chưa hoàn tất/hủy) và `Trip.has_open_issues` (boolean property: kiểm tra sự cố `status == 'OPEN'`)
- [X] T003 [P] Bổ sung các loại sự kiện mới vào enum `TripEventType` trong `src/models/trip_event.py` gồm `ISSUE_LOGGED`, `ISSUE_RESOLVED`, và `SCHEDULE_DELAYED` trích dẫn từ `data-model.md`
- [X] T004 [P] Tạo Pydantic v2 schemas cho Incident & Delay Management (`CreateTripIssueRequest`, `ResolveTripIssueRequest`, `RescheduleTripRequest`, `TripIssueItem`, `ConflictBookingItem`, `RescheduleResponse`) trong `src/schemas/trip.py` tuân thủ `contracts/incident-api.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Xây dựng tầng Data Access Layer cho sự cố, nâng cấp repository lịch trình và chuẩn bị dữ liệu kiểm thử

⚠️ **CRITICAL**: Không bắt đầu triển khai các User Story trước khi Phase 2 hoàn thành.

- [X] T005 Nâng cấp `TripIssueRepository` trong `src/repositories/trip_issue_repo.py` bổ sung các phương thức: `create_issue` với các trường mở rộng, `resolve_issue` cập nhật `resolution_notes` và `resolved_at`, `get_open_issues_count` theo `trip_id`, và `get_issues_by_trip` sắp xếp theo thời gian mới nhất
- [X] T006 [P] Nâng cấp `ResourceBookingRepository` trong `src/repositories/booking_repo.py` bổ sung các phương thức: `find_future_conflicts_for_resources` (quét các booking xe tải và tài xế trong khoảng thời gian gia hạn) và `extend_booking_end_time` (cập nhật `end_time` mới cho booking của chuyến hiện tại)
- [X] T007 [P] Nâng cấp `TripRepository` trong `src/repositories/trip_repo.py` bổ sung logic lọc theo cờ `has_issues` (chuyến có sự cố OPEN) và cờ `is_delayed` (chuyến có `estimated_end_time < now` và chưa kết thúc)
- [X] T008 Bổ sung dữ liệu mẫu Chuyến hàng (`Trip`) phát sinh sự cố hỏng xe và chuyến hàng quá hạn vận hành trong `src/core/seed.py` phục vụ kiểm thử giao diện

**Checkpoint**: Nền tảng dữ liệu và Repository sẵn sàng - các User Story bắt đầu triển khai.

---

## Phase 3: User Story 1 - Ghi nhận và Đóng Sự Cố Vận Chuyển (Priority: P1) 🎯 MVP

**Goal**: Cho phép Điều phối viên (`DSP`) lập biên bản sự cố phát sinh (`OPEN`) với đầy đủ phân loại, người xử lý, dự kiến khắc phục; và đóng sự cố (`RESOLVED`) khi hoàn tất kèm ghi chú giải pháp. Chuyến hàng không bị tự động hoàn tất và không tự đổi giá (tuân thủ SAL-08).

**Independent Test**: Chạy `pytest tests/unit/test_incidents.py` - kiểm tra lập sự cố thành công, đóng sự cố yêu cầu bắt buộc `resolution_notes`, từ chối đóng sự cố đã giải quyết, và xác nhận chuyến hàng giữ nguyên trạng thái vận hành.

### Tests for User Story 1 (TDD - Write first) ⚠️
- [X] T009 [P] [US1] Viết unit tests trong `tests/unit/test_incidents.py` kiểm tra: lập sự cố thành công với trạng thái `OPEN`, từ chối lập sự cố thiếu mô tả hoặc loại sự cố, đóng sự cố thành công sang `RESOLVED`, từ chối đóng sự cố nếu thiếu `resolution_notes`, và xác nhận trạng thái chuyến hàng không bị thay đổi
- [X] T010 [P] [US1] Viết contract tests cho các endpoints `POST /api/v1/trips/{id}/issues` và `POST /api/v1/trips/{id}/issues/{issue_id}/resolve` trong `tests/contract/test_incident_api.py`

### Implementation for User Story 1
- [X] T011 [US1] Xây dựng service `IncidentService` trong `src/services/incident_service.py` với phương thức `log_issue` (tạo `TripIssue`, ghi sự kiện `ISSUE_LOGGED`) và phương thức `resolve_issue` (cập nhật `resolution_notes`, đổi sang `RESOLVED`, ghi sự kiện `ISSUE_RESOLVED`) trong Atomic Transaction
- [X] T012 [US1] Hiện thực hóa REST API endpoints `POST /api/v1/trips/{id}/issues` và `POST /api/v1/trips/{id}/issues/{issue_id}/resolve` trong `src/api/v1/trips.py` áp dụng bảo vệ `require_role(["DSP"])`
- [X] T013 [US1] Hiện thực hóa Web controllers `POST /trips/{id}/issues` và `POST /trips/{id}/issues/{issue_id}/resolve` trong `src/web/trips.py`
- [X] T014 [US1] Tích hợp Modal Báo Cáo Sự Cố (`createIssueModal`) và Modal Giải Quyết Sự Cố (`resolveIssueModal`) trên giao diện `src/templates/trips/detail.html`

**Checkpoint**: User Story 1 hoàn thành độc lập và kiểm thử pass 100%. Đạt mốc MVP!

---

## Phase 4: User Story 2 - Phát hiện và Cảnh báo Quá hạn Vận hành (Priority: P1)

**Goal**: Hệ thống tự động xác định và hiển thị cờ cảnh báo "Quá hạn vận hành" (`DELAYED` / `OVERDUE`) cho các chuyến hàng chưa kết thúc khi thời gian hiện tại vượt quá `estimated_end_time`. Tuyệt đối không tự suy diễn vị trí GPS hay tự đổi trạng thái giao.

**Independent Test**: Chạy `pytest tests/unit/test_incidents.py` và `tests/integration/test_incident_lifecycle.py` - kiểm tra thuộc tính `is_delayed` trả về `True` khi quá hạn, trả về `False` khi chuyến chưa quá hạn hoặc đã `DELIVERED`/`COMPLETED`/`CANCELLED`.

### Tests for User Story 2 (TDD - Write first) ⚠️
- [X] T015 [P] [US2] Viết unit tests trong `tests/unit/test_incidents.py` kiểm tra logic tính toán `is_delayed`: chuyến đang chạy quá hạn trả về `True`, chuyến chưa đến hạn trả về `False`, chuyến đã `DELIVERED`/`COMPLETED` quá hạn vẫn trả về `False`
- [X] T016 [P] [US2] Viết integration test trong `tests/integration/test_incident_lifecycle.py` kiểm tra hiển thị cờ quá hạn trên danh sách và chi tiết chuyến, xác nhận cờ biến mất ngay sau khi chuyến chuyển sang `DELIVERED`

### Implementation for User Story 2
- [X] T017 [US2] Hiện thực hóa helper tính toán thời gian trễ và tích hợp thuộc tính `is_delayed` vào controller xem chi tiết `trip_detail_view` trong `src/web/trips.py`
- [X] T018 [US2] Cập nhật giao diện `src/templates/trips/detail.html` hiển thị banner cảnh báo quá hạn vận hành nổi bật (alert màu đỏ/cam hiển thị thời gian đã trễ) và cập nhật badge quá hạn trên `src/templates/trips/list.html`

---

## Phase 5: User Story 3 - Điều chỉnh Lùi Thời gian & Kiểm soát Xung đột Lịch Tương lai (Priority: P2)

**Goal**: Cho phép Điều phối viên (`DSP`) cập nhật gia hạn `estimated_end_time` khi gặp chậm trễ; hệ thống kiểm tra và cảnh báo chi tiết các booking tương lai bị chồng lấn; giữ nguyên lịch hiện tại và duy trì quy tắc BR-09 (nguồn lực đang bận không được nhận việc mới).

**Independent Test**: Chạy `pytest tests/unit/test_reschedule.py` - kiểm tra gia hạn không xung đột thành công (cập nhật booking `end_time`); kiểm tra gia hạn có xung đột: giữ lịch hiện tại, trả về danh sách booking xung đột (HTTP 409), và kiểm tra chuyến kế tiếp bị chặn nhận hàng theo BR-09.

### Tests for User Story 3 (TDD - Write first) ⚠️
- [X] T019 [P] [US3] Viết unit tests trong `tests/unit/test_reschedule.py` kiểm tra gia hạn hợp lệ, từ chối mốc thời gian trước `estimated_start_time`, phát hiện chính xác các booking tương lai bị xung đột cho cả xe tải và tài xế (vận tải lẫn thuê xe), và xác nhận quy tắc BR-09 chặn nhận hàng đơn kế tiếp
- [X] T020 [P] [US3] Viết contract test cho endpoint `POST /api/v1/trips/{id}/reschedule` trong `tests/contract/test_incident_api.py`

### Implementation for User Story 3
- [X] T021 [US3] Hiện thực hóa phương thức `reschedule_trip` trong `src/services/incident_service.py` thực hiện: xác thực mốc thời gian, quét xung đột với `find_future_conflicts_for_resources`, cập nhật `Trip.estimated_end_time` và `ResourceBooking.end_time`, ghi nhận sự kiện `SCHEDULE_DELAYED` trong Atomic Transaction
- [X] T022 [US3] Hiện thực hóa REST API endpoint `POST /api/v1/trips/{id}/reschedule` trong `src/api/v1/trips.py` áp dụng bảo vệ `require_role(["DSP"])`
- [X] T023 [US3] Hiện thực hóa Web controller `POST /trips/{id}/reschedule` trong `src/web/trips.py` hỗ trợ xử lý cảnh báo xung đột lịch
- [X] T024 [US3] Xây dựng Modal Gia Hạn Lịch (`rescheduleModal`) và Modal Cảnh Báo Xung Đột Lịch Trình (`conflictWarningModal`) trên giao diện `src/templates/trips/detail.html`

---

## Phase 6: User Story 4 - Nhật ký Sự cố Toàn diện & Dòng Thời Gian Audit (Priority: P3)

**Goal**: Trực quan hóa toàn bộ danh sách sự cố và tiến độ giải quyết trên giao diện chi tiết chuyến hàng; hiển thị các mốc sự kiện `ISSUE_LOGGED`, `ISSUE_RESOLVED`, `SCHEDULE_DELAYED` trên Dòng thời gian (Timeline).

**Independent Test**: Chạy `pytest tests/integration/test_incident_lifecycle.py` - kiểm tra các sự kiện được lưu vết đầy đủ trong `trip_events` và hiển thị trực quan trên giao diện chi tiết.

### Tests for User Story 4 (TDD - Write first) ⚠️
- [X] T025 [P] [US4] Viết integration test trong `tests/integration/test_incident_lifecycle.py` xác nhận thứ tự sự kiện trên dòng thời gian từ khi lập sự cố, gia hạn lịch, đến khi giải quyết sự cố

### Implementation for User Story 4
- [X] T026 [US4] Cập nhật bảng "Nhật Ký Sự Cố Chuyến Hàng" và khối Dòng thời gian trên `src/templates/trips/detail.html` hiển thị đầy đủ thông tin: Người xử lý, Dự kiến khắc phục, Kết quả xử lý, và các huy hiệu biểu tượng sự kiện theo `frontend/DESIGN.md`

---

## Phase 7: User Story 5 - Bộ Lọc Chuyến Hàng Có Sự Cố/Quá Hạn & Phân Quyền RBAC (Priority: P3)

**Goal**: Thêm tab bộ lọc cho các chuyến hàng đang có sự cố hoặc quá hạn vận hành; bảo vệ phân quyền nghiêm ngặt (chỉ `DSP` được thao tác ghi, `SAL`/`MGR` chỉ có quyền xem với HTTP 403 Forbidden).

**Independent Test**: Chạy `pytest tests/integration/test_incident_lifecycle.py` - kiểm tra tài khoản `SAL` và `MGR` xem được danh mục và chi tiết nhưng bị trả về HTTP 403 Forbidden khi cố gắng gửi request ghi nhận sự cố, đóng sự cố hoặc gia hạn lịch.

### Tests for User Story 5 (TDD - Write first) ⚠️
- [X] T027 [P] [US5] Viết integration test trong `tests/integration/test_incident_lifecycle.py` kiểm tra bảo vệ RBAC cho tất cả endpoints sự cố và gia hạn lịch, cùng kiểm tra hoạt động của bộ lọc `has_issues` và `is_delayed`

### Implementation for User Story 5
- [X] T028 [US5] Cập nhật giao diện danh mục chuyến hàng `src/templates/trips/list.html` bổ sung các tab lọc "Có Sự Cố" (`has_issues`) và "Quá Hạn Vận Hành" (`is_delayed`) kèm số lượng đếm trực quan

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Tự động hóa cập nhật schema cơ sở dữ liệu SQLite và nghiệm thu chất lượng toàn diện

- [X] T029 [P] Tự động kiểm tra và thêm các cột mới cho `trip_issues` (`occurred_at`, `handled_by`, `estimated_resolution_time`, `resolution_notes`, `resolved_at`) trong hàm `lifespan` tại `src/main.py`
- [X] T030 Thực thi toàn bộ bộ kiểm thử tự động `pytest tests/ -v` xác nhận 100% test cases (TRN-01, Auth, TRN-02, TRN-03, TRN-04, và TRN-05) đạt trạng thái PASS

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)**: Mở rộng `TripIssue`, `Trip`, `TripEventType`, và Pydantic schemas.
- **Phase 2 (Foundational)**: Xây dựng Repositories cho sự cố và kiểm tra xung đột lịch trình ➔ KHÓA (BLOCK) toàn bộ các User Story.
- **Phase 3 (User Story 1 - Sự cố MVP)**: Triển khai phương thức lập sự cố, đóng sự cố và Modal giao diện.
- **Phase 4 (User Story 2 - Quá hạn vận hành)**: Tính toán cờ quá hạn động và hiển thị cảnh báo.
- **Phase 5 (User Story 3 - Gia hạn & Xung đột tương lai)**: Kế thừa từ lịch trình; phát hiện xung đột và bảo vệ BR-09.
- **Phase 6 (User Story 4 - Audit Timeline)**: Hoàn thiện trực quan hóa sự kiện và nhật ký.
- **Phase 7 (User Story 5 - Bộ lọc & RBAC)**: Tích hợp bộ lọc danh mục và kiểm soát bảo mật phân quyền.
- **Phase 8 (Polish)**: Auto-migration SQLite và nghiệm thu 100% test suite.

### Parallel Opportunities
- T002, T003, T004 có thể làm song song trong Phase 1.
- T006, T007 có thể làm song song trong Phase 2.
- T009 và T010 (tests cho US1) có thể viết song song.
- T015, T016, T019, T020, T025, T027 (tests cho các User Stories) có thể chuẩn bị song song.
- T029 có thể làm song song với các bước hoàn thiện tài liệu.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Hoàn thành Phase 1 (Setup) và Phase 2 (Foundational).
2. Hoàn thành Phase 3: User Story 1 (Lập biên bản sự cố và đóng sự cố).
3. **DỪNG LẠI & KIỂM THỬ ĐỘC LẬP**: Chạy `pytest tests/unit/test_incidents.py` xác nhận đạt mốc MVP!

### Incremental Delivery
1. Setup + Foundational ➔ Sẵn sàng hạ tầng lưu sự cố và quét xung đột.
2. User Story 1 (Sự cố MVP) ➔ Nghiệm thu lập và đóng sự cố.
3. User Story 2 (Cảnh báo quá hạn) ➔ Nghiệm thu phát hiện trễ tiến độ.
4. User Story 3 (Gia hạn & Xung đột) ➔ Nghiệm thu xử lý lùi lịch và bảo vệ BR-09.
5. User Story 4 (Audit Timeline) ➔ Nghiệm thu nhật ký và lịch sử kiểm toán.
6. User Story 5 (Bộ lọc & RBAC) ➔ Nghiệm thu bảo mật phân quyền và tra cứu.
7. Phase 8 (Polish) ➔ Nghiệm thu toàn diện 100% test suite.
