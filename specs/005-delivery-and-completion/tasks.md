# Tasks: TRN-04 Xác nhận giao hàng và hoàn tất (Delivery Confirmation & Trip Completion)

**Input**: Design documents from `specs/005-delivery-and-completion/`  
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/delivery-api.yaml](contracts/delivery-api.yaml), [quickstart.md](quickstart.md)  
**Constitution**: Tuân thủ nghiêm ngặt 5 nguyên tắc trong [.specify/memory/constitution.md](../../.specify/memory/constitution.md)

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`
- **[P]**: Có thể chạy song song (khác file, không phụ thuộc task chưa xong)
- **[Story]**: Gán nhãn User Story (`[US1]`, `[US2]`, `[US3]`, `[US4]`, `[US5]`)
- Mô tả kèm đường dẫn file cụ thể và trích dẫn ràng buộc canonical từ `data-model.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Mở rộng cấu trúc model Chuyến hàng và khởi tạo các thực thể Bằng chứng POD và Sự cố

- [X] T001 Mở rộng model `Trip` trong `src/models/trip.py` bổ sung các cột theo dõi mốc trích dẫn canonical constraints từ `data-model.md` cho `Trip.actual_delivery_time` (DATETIME, NULLABLE), `Trip.actual_completed_time` (DATETIME, NULLABLE), `Trip.recipient_name` (VARCHAR(100), NULLABLE), `Trip.delivery_notes` (VARCHAR(500), NULLABLE), `Trip.delivery_recorded_at` (DATETIME, NULLABLE), `Trip.completed_recorded_at` (DATETIME, NULLABLE), và thiết lập quan hệ `relationship` tới `TripEvidence` và `TripIssue`
- [X] T002 [P] Tạo SQLAlchemy model `TripEvidence` trong `src/models/trip_evidence.py` trích dẫn canonical constraints từ `data-model.md` cho `TripEvidence.trip_id` (INTEGER, NOT NULL, FOREIGN KEY trips.id ON DELETE CASCADE, INDEX), `TripEvidence.file_path` (VARCHAR(500), NOT NULL), `TripEvidence.file_name` (VARCHAR(255), NOT NULL), `TripEvidence.file_size_bytes` (INTEGER, NOT NULL), `TripEvidence.mime_type` (VARCHAR(100), NOT NULL), `TripEvidence.evidence_type` (VARCHAR(50), NOT NULL, DEFAULT 'POD'), `TripEvidence.uploaded_by_user_id` (FOREIGN KEY users.id), và `TripEvidence.created_at` (DATETIME, NOT NULL, DEFAULT UTC NOW). Cập nhật `src/models/__init__.py`.
- [X] T003 [P] Tạo SQLAlchemy model `TripIssue` trong `src/models/trip_issue.py` trích dẫn canonical constraints từ `data-model.md` cho `TripIssue.trip_id` (INTEGER, NOT NULL, FOREIGN KEY trips.id ON DELETE CASCADE, INDEX), `TripIssue.issue_type` (VARCHAR(50), NOT NULL), `TripIssue.description` (VARCHAR(1000), NOT NULL), `TripIssue.status` (VARCHAR(20), NOT NULL, DEFAULT 'OPEN'), `TripIssue.reported_by_user_id` (FOREIGN KEY users.id), và `TripIssue.created_at` (DATETIME, NOT NULL, DEFAULT UTC NOW). Cập nhật `src/models/__init__.py`.
- [X] T004 [P] Bổ sung các loại sự kiện mới vào `TripEventType` trong `src/models/trip_event.py` gồm `DELIVERY_CONFIRMED`, `DELIVERY_FAILED`, và `TRIP_COMPLETED`
- [X] T005 [P] Tạo Pydantic v2 schemas cho Delivery & Completion (`RecordDeliveryRequest`, `CompleteTripRequest`, `TripEvidenceItem`, `TripIssueItem`, `TripEvidenceResponse`) trong `src/schemas/trip.py` tuân thủ `contracts/delivery-api.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Xây dựng tầng Data Access Layer cho chứng từ và sự cố, nâng cấp repository lịch trình và chuẩn bị thư mục lưu tệp

⚠️ **CRITICAL**: Không bắt đầu triển khai các User Story trước khi Phase 2 hoàn thành.

- [X] T006 Xây dựng `TripEvidenceRepository` trong `src/repositories/trip_evidence_repo.py` hỗ trợ lưu chứng từ POD, truy vấn danh sách chứng từ theo `trip_id`, đếm số lượng chứng từ, và truy vấn theo `evidence_id`
- [X] T007 [P] Xây dựng `TripIssueRepository` trong `src/repositories/trip_issue_repo.py` hỗ trợ tạo bản ghi sự cố vận chuyển và truy vấn sự cố theo `trip_id`
- [X] T008 [P] Nâng cấp `ResourceBookingRepository` trong `src/repositories/booking_repo.py` bổ sung phương thức `complete_bookings_for_trip` chuyển trạng thái booking của Xe tải và Tài xế từ `IN_PROGRESS` sang `COMPLETED` và cập nhật `end_time = actual_completed_time`
- [X] T009 Khởi tạo thư mục lưu trữ tệp an toàn `src/static/uploads/evidence/` và bổ sung dữ liệu mẫu Chuyến hàng (`Trip`) ở trạng thái `IN_TRANSIT` và `DELIVERED` trong `src/core/seed.py` phục vụ kiểm thử

**Checkpoint**: Nền tảng dữ liệu, Repository và thư mục lưu trữ sẵn sàng - các User Story bắt đầu triển khai.

---

## Phase 3: User Story 1 - Ghi nhận Giao hàng Thành công kèm Bằng chứng POD (Priority: P1) 🎯 MVP

**Goal**: Cho phép điều phối viên xác nhận giao hàng thành công cho chuyến hàng `IN_TRANSIT`, lưu thông tin người nhận, tải lên ít nhất một tệp chứng từ POD (PDF/JPG/PNG), chuyển trạng thái chuyến sang `DELIVERED` và ghi sự kiện vào dòng thời gian.

**Independent Test**: Chạy `pytest tests/unit/test_delivery.py` - kiểm tra xác nhận giao hàng hợp lệ thành công (chuyến sang `DELIVERED`, lưu tệp chứng từ POD, tạo sự kiện `DELIVERY_CONFIRMED`), và từ chối nếu chuyến không ở `IN_TRANSIT`, thiếu tệp POD hoặc thời điểm giao trước thời điểm nhận hàng.

### Tests for User Story 1 (TDD - Write first) ⚠️
- [X] T010 [P] [US1] Viết unit tests trong `tests/unit/test_delivery.py` kiểm tra giao hàng thành công từ `IN_TRANSIT` sang `DELIVERED`, kiểm tra từ chối khi không có tệp POD, kiểm tra từ chối khi chuyến ở các trạng thái khác (`UNASSIGNED`, `ASSIGNED`, `PICKED_UP`), và từ chối khi `actual_delivery_time < actual_pickup_time`
- [X] T011 [P] [US1] Viết contract test cho endpoint `POST /api/v1/trips/{id}/deliver` trong `tests/contract/test_delivery_api.py`

### Implementation for User Story 1
- [X] T012 [US1] Xây dựng service `DeliveryService` trong `src/services/delivery_service.py` với phương thức `record_delivery` xử lý xác thực trạng thái `IN_TRANSIT`, kiểm tra mốc thời gian, lưu tệp POD an toàn với tiền tố UUID, tạo bản ghi `TripEvidence`, cập nhật chuyến sang `DELIVERED`, và ghi nhận `TripEvent` trong một Atomic Transaction
- [X] T013 [US1] Hiện thực hóa REST API endpoint `POST /api/v1/trips/{id}/deliver` hỗ trợ multipart/form-data trong `src/api/v1/trips.py` áp dụng bảo vệ `require_role(["DSP"])`
- [X] T014 [US1] Hiện thực hóa Web controller `GET /trips/{id}/deliver` và `POST /trips/{id}/deliver` trong `src/web/trips.py`
- [X] T015 [US1] Xây dựng giao diện ghi nhận giao hàng `src/templates/trips/deliver.html` theo `frontend/DESIGN.md` có đầy đủ các trường thời điểm giao, họ tên người nhận, kết quả giao, vùng kéo thả/chọn tệp POD và client-side validation kiểm tra định dạng và dung lượng tệp $\le 10$ MB

**Checkpoint**: User Story 1 hoàn thành độc lập và kiểm thử pass 100%. Đạt mốc MVP!

---

## Phase 4: User Story 2 - Chốt Hoàn tất Chuyến hàng và Giải phóng Nguồn lực (Priority: P1)

**Goal**: Cho phép điều phối viên đóng hoàn tất chuyến hàng (`DELIVERED` ➔ `COMPLETED`) khi đã có đủ chứng từ POD và không còn phụ phí PENDING; lưu thời điểm giải phóng xe/tài xế; tự động chuyển trạng thái booking sang `COMPLETED`, giải phóng tài nguyên lập tức cho các đơn sau theo BR-09.

**Independent Test**: Chạy `pytest tests/unit/test_delivery.py` và `tests/integration/test_delivery_lifecycle.py` - kiểm tra hoàn tất chuyến thành công, booking của xe/tài xế sang `COMPLETED`, hàm `has_in_progress_booking` trả về False, và từ chối hoàn tất nếu thiếu POD, thời điểm hoàn tất ở tương lai hoặc có phụ phí PENDING.

### Tests for User Story 2 (TDD - Write first) ⚠️
- [X] T016 [P] [US2] Viết unit tests trong `tests/unit/test_delivery.py` kiểm tra đóng chuyến `COMPLETED` thành công, kiểm tra từ chối khi chuyến chưa ở `DELIVERED`, kiểm tra từ chối khi thiếu chứng từ POD, và từ chối khi `actual_completed_time` ở tương lai hoặc trước thời điểm giao
- [X] T017 [P] [US2] Viết integration test trong `tests/integration/test_delivery_lifecycle.py` xác nhận sau khi chuyến `COMPLETED`, Xe tải và Tài xế được giải phóng hoàn toàn và có thể nhận hàng (`PICKED_UP`) ngay ở chuyến kế tiếp mà không bị chặn bởi BR-09

### Implementation for User Story 2
- [X] T018 [US2] Hiện thực hóa phương thức `complete_trip` trong `src/services/delivery_service.py` kiểm tra điều kiện chứng từ POD, kiểm tra mốc thời gian giải phóng, cập nhật trạng thái chuyến sang `COMPLETED`, chuyển các booking liên quan sang `COMPLETED`, và ghi `TripEvent` `TRIP_COMPLETED` trong một Atomic Transaction
- [X] T019 [US2] Hiện thực hóa REST API endpoint `POST /api/v1/trips/{id}/complete` trong `src/api/v1/trips.py` áp dụng bảo vệ `require_role(["DSP"])`
- [X] T020 [US2] Bổ sung Web action `POST /trips/{id}/complete` trong `src/web/trips.py` và tích hợp Modal xác nhận hoàn tất chuyến hàng kèm nhập mốc thời gian giải phóng trên `src/templates/trips/detail.html`

---

## Phase 5: User Story 3 - Xử lý Giao hàng Không Thành công & Ghi nhận Sự cố (Priority: P2)

**Goal**: Cho phép ghi nhận trường hợp giao thất bại (`FAILED`), giữ nguyên trạng thái chuyến ở `IN_TRANSIT` (không đánh dấu đã giao), tự động lập bản ghi sự cố `TripIssue`, và chặn đóng chuyến.

**Independent Test**: Chạy `pytest tests/unit/test_delivery.py` - gửi kết quả giao hàng thất bại kèm mô tả lý do; kiểm tra chuyến vẫn ở `IN_TRANSIT`, bản ghi `TripIssue` mới được tạo với trạng thái `OPEN`, và chuyến không thể hoàn tất.

### Tests for User Story 3 (TDD - Write first) ⚠️
- [X] T021 [P] [US3] Viết unit và integration test trong `tests/unit/test_delivery.py` và `tests/integration/test_delivery_lifecycle.py` kiểm tra xử lý giao hàng thất bại, tạo `TripIssue`, giữ nguyên `IN_TRANSIT`, và chặn hoàn tất

### Implementation for User Story 3
- [X] T022 [US3] Tích hợp luồng giao hàng thất bại (`result == 'FAILED'`) vào phương thức `record_delivery` tại `src/services/delivery_service.py` gọi `TripIssueRepository` tạo sự cố, lưu ảnh bằng chứng sự cố nếu có, giữ nguyên trạng thái `IN_TRANSIT`, và ghi `TripEvent` `DELIVERY_FAILED`
- [X] T023 [US3] Cập nhật giao diện `src/templates/trips/deliver.html` với chuyển đổi giao diện động (khi chọn "Giao thất bại" thì hiển thị ô nhập lý do sự cố và loại sự cố), và bổ sung khu vực hiển thị "Nhật ký sự cố" trên `src/templates/trips/detail.html`

---

## Phase 6: User Story 4 - Quản lý và Tra cứu Tệp Bằng chứng Bàn giao POD (Priority: P2)

**Goal**: Hiển thị danh sách các tệp chứng từ POD đã tải lên, hỗ trợ tải về hoặc xem trực tiếp tệp an toàn, và cho phép bổ sung thêm chứng từ phụ trước khi hoàn tất.

**Independent Test**: Chạy `pytest tests/contract/test_delivery_api.py` - kiểm tra gọi API tải danh sách chứng từ, tải tệp chứng từ trả về đúng Content-Type và dung lượng tệp; kiểm tra upload bổ sung chứng từ thành công.

### Tests for User Story 4 (TDD - Write first) ⚠️
- [X] T024 [P] [US4] Viết contract và integration tests trong `tests/contract/test_delivery_api.py` và `tests/integration/test_delivery_lifecycle.py` kiểm tra lấy danh sách chứng từ, tải bổ sung chứng từ và endpoint download tệp chứng từ

### Implementation for User Story 4
- [X] T025 [US4] Hiện thực hóa REST API endpoints `GET /api/v1/trips/{id}/evidence`, `POST /api/v1/trips/{id}/evidence`, và `GET /api/v1/trips/{id}/evidence/{evidence_id}/download` trong `src/api/v1/trips.py`
- [X] T026 [US4] Hiện thực hóa Web controller download tệp chứng từ `GET /trips/{id}/evidence/{evidence_id}/download` và upload bổ sung `POST /trips/{id}/evidence` trong `src/web/trips.py` trả về `FileResponse` an toàn
- [X] T027 [US4] Cập nhật màn hình `src/templates/trips/detail.html` hiển thị khối "Chứng từ & Bằng chứng bàn giao (POD)" với danh sách tệp trực quan, nút xem trước/tải về và nút mở Modal tải thêm chứng từ

---

## Phase 7: User Story 5 - Dòng thời gian Lịch sử & Phân quyền Truy cập (Priority: P3)

**Goal**: Trực quan hóa toàn bộ hành trình sự kiện trên Vertical Timeline từ nhận hàng đến hoàn tất (và các sự cố nếu có); bảo vệ phân quyền chặt chẽ (chỉ `DSP` được thao tác ghi, `SAL`/`MGR` chỉ có quyền xem).

**Independent Test**: Chạy `pytest tests/integration/test_delivery_lifecycle.py` - kiểm tra tài khoản `sal` và `mgr` xem được đầy đủ chi tiết chứng từ và timeline nhưng nhận mã 403 Forbidden khi cố gắng gửi yêu cầu giao hàng hoặc hoàn tất đơn.

### Tests for User Story 5 (TDD - Write first) ⚠️
- [X] T028 [P] [US5] Viết integration test trong `tests/integration/test_delivery_lifecycle.py` kiểm tra phân quyền RBAC cho các endpoint giao hàng và hoàn tất, cùng thứ tự các mốc sự kiện trên dòng thời gian

### Implementation for User Story 5
- [X] T029 [US5] Cập nhật Vertical Timeline trên `src/templates/trips/detail.html` hiển thị mốc `DELIVERY_CONFIRMED`, `DELIVERY_FAILED`, `TRIP_COMPLETED` kèm huy hiệu màu sắc chuẩn `frontend/DESIGN.md` và kiểm soát ẩn/hiện nút hành động theo vai trò `current_user.role`

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Tích hợp toàn diện vào ứng dụng, tự động hóa cập nhật schema cơ sở dữ liệu và nghiệm thu chất lượng

- [X] T030 [P] Cập nhật danh sách chuyến hàng `src/templates/trips/list.html` bổ sung các tab lọc `DELIVERED`, `COMPLETED`, huy hiệu màu sắc tương ứng, và nút mở form giao hàng trực tiếp cho các chuyến `IN_TRANSIT`
- [X] T031 Tự động kiểm tra và thêm các cột mới cho `trips` cũng như tạo bảng `trip_evidence` và `trip_issues` nếu thiếu trong hàm `lifespan` tại `src/main.py`
- [X] T032 Thực thi toàn bộ bộ kiểm thử tự động `pytest tests/ -v` xác nhận 100% test cases (cả TRN-01, Auth, TRN-02, TRN-03, và TRN-04) đạt trạng thái PASS

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)**: Mở rộng `Trip`, tạo `TripEvidence`, `TripIssue`, enum types và Pydantic schemas.
- **Phase 2 (Foundational)**: Xây dựng Repositories, chuẩn bị thư mục upload tệp và seed data ➔ KHÓA (BLOCK) toàn bộ các User Story.
- **Phase 3 (User Story 1 - Giao hàng MVP)**: Triển khai phương thức `record_delivery`, form giao hàng và lưu tệp POD.
- **Phase 4 (User Story 2 - Hoàn tất & Giải phóng)**: Kế thừa từ trạng thái `DELIVERED` của US1; giải phóng nguồn lực cho BR-09.
- **Phase 5 (User Story 3 - Xử lý giao thất bại)**: Nhánh xử lý ngoại lệ cho `record_delivery` và nhật ký sự cố.
- **Phase 6 (User Story 4 - Quản lý chứng từ POD)**: Quản lý tệp, xem trước, tải về và bổ sung chứng từ.
- **Phase 7 (User Story 5 - Timeline & Phân quyền)**: Hoàn thiện dòng thời gian toàn diện và kiểm soát RBAC.
- **Phase 8 (Polish)**: Cập nhật danh mục, auto-migration và nghiệm thu 100% test suite.

### Parallel Opportunities
- T001, T002, T003, T004, T005 có thể làm song song trong Phase 1.
- T006, T007, T008 có thể làm song song trong Phase 2.
- T010 và T011 (viết tests cho US1) có thể làm song song.
- T016, T017, T021, T024, T028 (viết tests cho US2, US3, US4, US5) có thể làm song song.
- T030 và T031 có thể làm song song trong Phase 8.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Hoàn thành Phase 1 (Setup) và Phase 2 (Foundational).
2. Hoàn thành Phase 3: User Story 1 (Giao hàng thành công + tải tệp POD).
3. **DỪNG LẠI & KIỂM THỬ ĐỘC LẬP**: Chạy `pytest tests/unit/test_delivery.py` xác nhận đạt mốc MVP!

### Incremental Delivery
1. Setup + Foundational ➔ Sẵn sàng hạ tầng lưu tệp và bảng dữ liệu.
2. User Story 1 (Giao hàng POD MVP) ➔ Nghiệm thu chuyển sang `DELIVERED`.
3. User Story 2 (Hoàn tất & Giải phóng) ➔ Nghiệm thu giải phóng xe và tài xế cho BR-09.
4. User Story 3 (Giao thất bại & Sự cố) ➔ Nghiệm thu xử lý ngoại lệ trung thực với thực tế.
5. User Story 4 (Quản lý chứng từ) ➔ Nghiệm thu xem trước và tải tệp POD.
6. User Story 5 (Timeline & RBAC) ➔ Nghiệm thu bảo mật phân quyền.
7. Phase 8 (Polish) ➔ Nghiệm thu toàn diện 100% test suite.
