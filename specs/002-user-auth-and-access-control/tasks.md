# Tasks: 002-user-auth-and-access-control

**Input**: Design documents from `specs/002-user-auth-and-access-control/`  
**Prerequisites**: [plan.md](file:///d:/PPA.MP08_GROUP3/specs/002-user-auth-and-access-control/plan.md), [spec.md](file:///d:/PPA.MP08_GROUP3/specs/002-user-auth-and-access-control/spec.md), [research.md](file:///d:/PPA.MP08_GROUP3/specs/002-user-auth-and-access-control/research.md), [data-model.md](file:///d:/PPA.MP08_GROUP3/specs/002-user-auth-and-access-control/data-model.md), [contracts/](file:///d:/PPA.MP08_GROUP3/specs/002-user-auth-and-access-control/contracts/), [quickstart.md](file:///d:/PPA.MP08_GROUP3/specs/002-user-auth-and-access-control/quickstart.md)  
**Constitution**: Tuân thủ 5 nguyên tắc trong [.specify/memory/constitution.md](file:///d:/PPA.MP08_GROUP3/.specify/memory/constitution.md)

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`
- **[P]**: Có thể thực hiện song song (khác file, không phụ thuộc task chưa hoàn thành)
- **[Story]**: Gán nhãn User Story (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Mô tả kèm đường dẫn file cụ thể và trích dẫn ràng buộc canonical từ `data-model.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Bổ sung thư viện bảo mật và cấu hình phiên làm việc

- [X] T001 Cập nhật thư viện `bcrypt>=5.0.0` trong `requirements.txt` phục vụ băm mật khẩu bảo mật
- [X] T002 [P] Xây dựng các hàm băm và xác thực mật khẩu bcrypt trong `src/core/security.py`
- [X] T003 [P] Cấu hình `SessionMiddleware` với Signed Cookie an toàn (HTTP-Only, SameSite=Lax) trong `src/main.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Hạ tầng dữ liệu tài khoản và tầng dependencies xác thực phiên dùng chung

⚠️ **CRITICAL**: Không bắt đầu triển khai các User Story trước khi Phase 2 hoàn thành.

- [X] T004 Tạo SQLAlchemy model `User` trong `src/models/user.py` trích dẫn canonical constraints từ `data-model.md` cho `User.username` (VARCHAR(50), UNIQUE, INDEX), `User.password_hash` (VARCHAR(255), NOT NULL), `User.role` (CHECK role IN ('DSP', 'SAL', 'MGR')), và `User.is_active` (BOOLEAN, DEFAULT TRUE)
- [X] T005 [P] Xây dựng `UserRepository` trong `src/repositories/user_repo.py` hỗ trợ tra cứu theo username và ID
- [X] T006 [P] Tạo Pydantic v2 schemas cho Auth (`LoginRequest`, `UserSession`, `AuthResponse`, `UserProfileResponse`) trong `src/schemas/auth.py` tuân thủ `contracts/auth-api.yaml`
- [X] T007 [P] Xây dựng authentication và authorization dependencies (`get_current_user`, `require_role`) trong `src/core/security.py`
- [X] T008 Cập nhật hàm `seed_initial_data` trong `src/core/seed.py` để tự động nạp sẵn 3 tài khoản demo (`dsp_user`, `sal_user`, `mgr_user`) với mật khẩu băm bcrypt

**Checkpoint**: Nền tảng xác thực sẵn sàng - các User Story bắt đầu triển khai độc lập.

---

## Phase 3: User Story 1 - Đăng nhập tài khoản bằng Username & Password (Priority: P1) 🎯 MVP

**Goal**: Cho phép người dùng đăng nhập bằng tên đăng nhập và mật khẩu, thiết lập session cookie an toàn và chuyển hướng vào dashboard.

**Independent Test**: Chạy `pytest tests/unit/test_auth.py` - kiểm tra xác thực username/password đúng, từ chối mật khẩu sai, từ chối tài khoản bị khóa.

### Tests for User Story 1 (TDD - Write first) ⚠️
- [X] T009 [P] [US1] Viết unit tests kiểm tra logic xác thực mật khẩu, đăng nhập thành công, và từ chối mật khẩu sai trong `tests/unit/test_auth.py`

### Implementation for User Story 1
- [X] T010 [US1] Hiện thực hóa `AuthService` trong `src/services/auth_service.py` xử lý xác thực tài khoản, kiểm tra `is_active` và khởi tạo phiên làm việc
- [X] T011 [US1] Hiện thực hóa REST API login endpoint `POST /api/v1/auth/login` và `GET /api/v1/auth/me` trong `src/api/v1/auth.py` tuân thủ `contracts/auth-api.yaml`
- [X] T012 [US1] Hiện thực hóa Web Login controller (`GET /login`, `POST /login`) trong `src/web/auth.py`
- [X] T013 [US1] Xây dựng template giao diện đăng nhập hiện đại trong `src/templates/auth/login.html` kế thừa `base.html` và đồng bộ `frontend/DESIGN.md`

**Checkpoint**: User Story 1 hoàn thành độc lập và kiểm thử pass 100%. Đạt mốc MVP!

---

## Phase 4: User Story 2 - Đăng xuất và Hủy phiên làm việc (Priority: P1)

**Goal**: Cho phép người dùng đăng xuất, xóa sạch dữ liệu phiên và cookie, bảo vệ không cho truy cập lại khi chưa đăng nhập.

**Independent Test**: Gọi endpoint `/logout`, kiểm tra session bị hủy, truy cập `/dashboard` bị chuyển hướng ngay về `/login`.

### Tests for User Story 2 (TDD - Write first) ⚠️
- [X] T014 [P] [US2] Viết test kiểm tra cơ chế xóa sạch session khi gọi logout trong `tests/unit/test_auth.py`

### Implementation for User Story 2
- [X] T015 [US2] Hiện thực hóa REST API logout endpoint `POST /api/v1/auth/logout` trong `src/api/v1/auth.py`
- [X] T016 [US2] Hiện thực hóa Web Logout router `GET /logout` trong `src/web/auth.py` xóa session và chuyển hướng về `/login?logged_out=true`
- [X] T017 [US2] Cập nhật Top Navigation Bar trong `src/templates/base.html` hiển thị tên người dùng đang đăng nhập, Badge vai trò và nút Đăng xuất trực quan

**Checkpoint**: User Story 1 và User Story 2 hoàn tất trọn vẹn vòng đời đăng nhập - đăng xuất.

---

## Phase 5: User Story 3 - Phân quyền theo vai trò (Role-Based Access Control - RBAC) (Priority: P2)

**Goal**: Bảo vệ toàn bộ các tuyến đường hệ thống, phân định quyền hạn giữa `DSP` (toàn quyền) và `SAL`/`MGR` (chỉ đọc), chặn các thao tác ghi dữ liệu trái quyền bằng mã HTTP 403 Forbidden.

**Independent Test**: Chạy `pytest tests/integration/test_rbac.py` - người dùng chưa đăng nhập bị chuyển hướng về `/login`, tài khoản `sal_user` gọi POST/PUT/DELETE bị trả HTTP 403.

### Tests for User Story 3 (TDD - Write first) ⚠️
- [X] T018 [P] [US3] Viết integration test trong `tests/integration/test_rbac.py` kiểm tra chuyển hướng khi chưa đăng nhập và chặn mã 403 đối với vai trò `SAL`

### Implementation for User Story 3
- [X] T019 [US3] Xây dựng trang thông báo lỗi phân quyền `src/templates/error/403.html` hiển thị giao diện thân thiện khi không đủ thẩm quyền
- [X] T020 [US3] Gắn dependency `get_current_user` và `require_role(["DSP"])` bảo vệ các endpoint ghi dữ liệu trong `src/api/v1/trucks.py` và `src/api/v1/drivers.py`
- [X] T021 [US3] Gắn dependency bảo vệ các router web trong `src/web/admin_trucks.py`, `src/web/admin_drivers.py`, và `src/web/dashboard.py`
- [X] T022 [US3] Cập nhật các nút thao tác nghiệp vụ trong `src/templates/trucks/list.html`, `src/templates/drivers/list.html`, và `src/templates/dashboard/index.html` chỉ hiển thị khi `current_user.role == 'DSP'`

**Checkpoint**: Toàn bộ hệ thống được bảo vệ an toàn với phân quyền RBAC đa vai trò.

---

## Phase 6: User Story 4 - Tiện ích chuyển đổi tài khoản thử nghiệm nhanh (Priority: P3)

**Goal**: Cung cấp thanh chọn 1-click trên màn hình đăng nhập để tự động điền tài khoản demo (`dsp_user`, `sal_user`, `mgr_user`).

**Independent Test**: Mở trang `/login`, bấm nút demo DSP hoặc SAL, kiểm tra thông tin form được điền chính xác.

- [X] T023 [US4] Bổ sung các nút bấm 1-Click Fill Demo Accounts trên giao diện `src/templates/auth/login.html`

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Tích hợp toàn diện, chuẩn hóa giao diện và nghiệm thu hệ thống

- [X] T024 [P] Đăng ký auth routers vào `src/main.py` và `src/api/v1/api_router.py`
- [X] T025 Thực thi toàn bộ bộ kiểm thử tự động `pytest tests/ -v` xác nhận 100% test cases (cả Auth và TRN-01) đạt trạng thái PASS

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)**: Thực hiện ngay lập tức.
- **Phase 2 (Foundational)**: Phụ thuộc vào Phase 1; KHÓA (BLOCK) toàn bộ các User Story.
- **Phase 3 (User Story 1 - Login)**: Bắt đầu ngay sau khi Phase 2 hoàn thành.
- **Phase 4 (User Story 2 - Logout)**: Kế thừa từ User Story 1.
- **Phase 5 (User Story 3 - RBAC)**: Phụ thuộc vào User Story 1 và các module Truck/Driver đã có.
- **Phase 6 (User Story 4 - Demo Switcher)**: Tích hợp trên giao diện Login.
- **Phase 7 (Polish)**: Nghiệm thu toàn diện test suite.

### Parallel Opportunities
- T002, T003 có thể làm song song trong Phase 1.
- T005, T006, T007 có thể làm song song trong Phase 2.
- T009, T014, T018 (viết tests) có thể chuẩn bị độc lập.

---

## Implementation Strategy

### MVP First (User Story 1 - Login)
1. Hoàn thành Setup + Foundational.
2. Hoàn thành User Story 1 (Trang `/login` + xác thực mật khẩu bcrypt).
3. **Nghiệm thu MVP**: Đăng nhập thành công với tài khoản `dsp_user`.

### Incremental Delivery
1. Setup + Foundational ➔ Sẵn sàng Model `User` và `bcrypt`.
2. Thêm US1 (Login) ➔ Xác thực phiên thành công (MVP).
3. Thêm US2 (Logout) ➔ Vòng đời phiên hoàn chỉnh.
4. Thêm US3 (RBAC) ➔ Phân quyền chặt chẽ DSP vs SAL.
5. Thêm US4 (Demo switcher) ➔ Trải nghiệm kiểm thử thuận tiện.
