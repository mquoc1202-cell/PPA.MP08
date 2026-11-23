# Feature Specification: 002-user-auth-and-access-control

**Feature Branch**: `002-user-auth-and-access-control`

**Created**: 2026-11-23

**Status**: Draft

**Input**: User description: "tạo module trang đăng nhập để có thể đăng nhập vào từng tài khoản trước chứ nhỉ"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Đăng nhập tài khoản bằng Username & Mật khẩu (Priority: P1 - MVP)

Là người dùng hệ thống (Điều phối viên DSP, Kinh doanh SAL, hoặc Quản lý MGR), tôi muốn đăng nhập vào hệ thống bằng tên đăng nhập và mật khẩu hợp lệ để truy cập vào các chức năng làm việc tương ứng với quyền hạn của mình.

**Why this priority**: Xác thực người dùng là cánh cổng bảo mật đầu tiên của hệ thống. Cần có thông tin danh tính để biết ai đang thao tác và kiểm soát phân quyền.

**Independent Test**: Có thể kiểm thử độc lập bằng cách mở trang `/login`, nhập tài khoản mẫu hợp lệ, xác nhận đăng nhập thành công, chuyển hướng vào `/dashboard`, thông tin tài khoản hiển thị trên Navbar; thử nhập sai mật khẩu và xác nhận hệ thống từ chối với thông báo thân thiện.

**Acceptance Scenarios**:

1. **Given** tài khoản hợp lệ tồn tại trong hệ thống (ví dụ: `dsp_user` với vai trò `DSP`), **When** người dùng nhập đúng tên đăng nhập và mật khẩu tại `/login` rồi gửi biểu mẫu, **Then** hệ thống thiết lập phiên làm việc an toàn (Session Cookie HTTP-Only), chuyển hướng về `/dashboard`, và hiển thị thông tin `dsp_user [DSP]` trên thanh điều hướng.
2. **Given** người dùng nhập sai tên đăng nhập hoặc mật khẩu, **When** gửi biểu mẫu đăng nhập, **Then** hệ thống từ chối đăng nhập, hiển thị thông báo lỗi "Tên đăng nhập hoặc mật khẩu không chính xác", và giữ nguyên tên đăng nhập đã nhập trên form.
3. **Given** tài khoản đang ở trạng thái bị vô hiệu hóa (`is_active = False`), **When** đăng nhập, **Then** hệ thống từ chối và thông báo "Tài khoản của bạn đã bị khóa, vui lòng liên hệ quản trị viên."

---

### User Story 2 - Đăng xuất và Hủy phiên làm việc (Priority: P1)

Là người dùng đang đăng nhập, tôi muốn đăng xuất khỏi hệ thống để bảo vệ an toàn tài khoản khi rời máy tính hoặc kết thúc ca làm việc.

**Why this priority**: Đảm bảo an toàn phiên làm việc, ngăn ngừa truy cập trái phép sau khi người dùng rời đi.

**Independent Test**: Đăng nhập vào hệ thống, bấm nút "Đăng xuất" trên thanh Navbar, xác minh phiên bị hủy hoàn toàn và bị chuyển hướng về `/login`. Thử bấm nút Back trên trình duyệt hoặc truy cập lại `/dashboard` phải bị chặn và chuyển hướng về `/login`.

**Acceptance Scenarios**:

1. **Given** người dùng đang đăng nhập hợp lệ, **When** bấm vào nút "Đăng xuất" (`/logout`), **Then** hệ thống xóa toàn bộ dữ liệu phiên trong session, vô hiệu hóa cookie và chuyển hướng về `/login?logged_out=true`.
2. **Given** người dùng đã đăng xuất, **When** cố tình mở lại bất kỳ URL quản trị nào (`/dashboard`, `/admin/trucks`, `/admin/drivers`), **Then** hệ thống chặn truy cập và chuyển hướng về `/login`.

---

### User Story 3 - Phân quyền theo vai trò (Role-Based Access Control - RBAC) (Priority: P2)

Là người quản trị hệ thống, tôi muốn phân quyền chặt chẽ giữa các vai trò `DSP` (Điều phối viên) và `SAL` (Nhân viên kinh doanh) / `MGR` (Quản lý) để đảm bảo nhân viên kinh doanh chỉ có quyền tra cứu thông tin (Read-only), không thể thực hiện điều phối hay thay đổi dữ liệu xe/tài xế.

**Why this priority**: Tuân thủ quy định phân quyền trong tài liệu nghiệp vụ vận tải gốc `03_Freight_Transportation.pdf` và `AGENTS.md`.

**Independent Test**: Đăng nhập với tài khoản `sal_user` (vai trò `SAL`), kiểm tra giao diện danh sách xe và tài xế không hiển thị các nút "Thêm", "Sửa", "Xóa". Cố tình gửi yêu cầu POST/PUT/DELETE trực tiếp và xác nhận hệ thống trả về HTTP 403 Forbidden.

**Acceptance Scenarios**:

1. **Given** người dùng đăng nhập với vai trò `SAL` hoặc `MGR`, **When** xem danh sách Đội Xe hoặc Danh mục Tài Xế, **Then** hệ thống chỉ hiển thị dữ liệu ở chế độ Xem (Read-only), ẩn các nút "Thêm Xe Mới", "Thêm Tài Xế Mới", nút "Sửa", và nút "Xóa".
2. **Given** người dùng vai trò `SAL` cố tình gửi yêu cầu tạo mới, chỉnh sửa, hoặc xóa tới các endpoint quản trị (`/admin/trucks/create`, `/admin/trucks/{id}/edit`, `/api/v1/trucks`), **When** backend kiểm tra quyền, **Then** hệ thống từ chối với mã HTTP 403 Forbidden và hiển thị giao diện thông báo lỗi `templates/error/403.html`.
3. **Given** người dùng đăng nhập với vai trò `DSP` (Điều phối viên), **When** truy cập các trang quản trị, **Then** hệ thống hiển thị đầy đủ các nút chức năng và cho phép thực thi mọi thao tác nghiệp vụ điều phối.

---

### User Story 4 - Tiện ích chuyển đổi tài khoản thử nghiệm nhanh (Priority: P3)

Là người dùng kiểm thử hoặc đánh giá hệ thống, tôi muốn trên trang đăng nhập có sẵn danh sách các tài khoản demo (`DSP`, `SAL`, `MGR`) để có thể chuyển đổi và trải nghiệm các vai trò khác nhau chỉ với 1 cú click.

**Why this priority**: Tăng tốc độ kiểm thử và trải nghiệm trực quan cho người dùng đánh giá.

**Independent Test**: Tại trang `/login`, bấm vào nút demo "Đăng nhập vai trò DSP", hệ thống tự động điền username/password và đăng nhập thành công.

**Acceptance Scenarios**:

1. **Given** người dùng tại trang `/login`, **When** bấm vào nút "Tài khoản mẫu: DSP (Điều phối)" hoặc "SAL (Kinh doanh)", **Then** hệ thống tự động điền thông tin tương ứng vào các ô nhập liệu giúp người dùng đăng nhập ngay lập tức.

---

### Edge Cases

- **Truy cập URL được bảo vệ khi chưa đăng nhập:** Nếu người dùng gõ trực tiếp `http://localhost:8000/admin/trucks/create`, hệ thống phải lưu lại đường dẫn gốc và chuyển hướng về `/login?next=%2Fadmin%2Ftrucks%2Fcreate` để sau khi đăng nhập thành công sẽ đưa người dùng về đúng trang mong muốn.
- **Session hết hạn hoặc cookie bị giả mạo:** Nếu cookie phiên không hợp lệ hoặc bị xóa, hệ thống xóa sạch session và chuyển hướng về `/login` kèm thông báo phiên đã kết thúc.
- **Tài khoản bị khóa giữa phiên làm việc:** Khi người dùng thực hiện thao tác tiếp theo, dependency kiểm tra trạng thái `is_active` trong database; nếu tài khoản đã bị khóa thì lập tức hủy session và từ chối thao tác.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống BẮT BUỘC cung cấp trang đăng nhập `/login` kế thừa chuẩn Design System từ `frontend/DESIGN.md`.
- **FR-002**: Hệ thống BẮT BUỘC mã hóa và xác thực mật khẩu người dùng bằng giải thuật băm một chiều an toàn (`bcrypt`), TUYỆT ĐỐI KHÔNG lưu mật khẩu dạng văn bản rõ (plain-text).
- **FR-003**: Hệ thống BẮT BUỘC duy trì phiên làm việc bằng Session Cookie an toàn (HTTP-Only, Secure, SameSite=Lax), tuân thủ nguyên tắc xác thực trong `AGENTS.md`.
- **FR-004**: Hệ thống BẮT BUỘC cung cấp chức năng đăng xuất `/logout` xóa sạch toàn bộ thông tin phiên làm việc.
- **FR-005**: Hệ thống BẮT BUỘC bảo vệ toàn bộ các tuyến đường nghiệp vụ (`/dashboard`, `/admin/*`, `/api/v1/*`), chặn người dùng chưa xác thực và chuyển hướng về `/login`.
- **FR-006**: Hệ thống BẮT BUỘC hỗ trợ phân quyền người dùng (Role-Based Access Control) với ít nhất 3 vai trò:
  - `DSP` (Điều phối viên): Toàn quyền thêm, sửa, đổi trạng thái và điều phối.
  - `SAL` (Nhân viên kinh doanh): Quyền chỉ đọc (Read-only).
  - `MGR` (Quản lý): Quyền chỉ đọc báo cáo tổng quan.
- **FR-007**: Khi người dùng không đủ thẩm quyền thực hiện thao tác (ví dụ `SAL` cố tình sửa xe hoặc gán chuyến), hệ thống BẮT BUỘC trả mã lỗi HTTP 403 Forbidden và hiển thị trang cảnh báo `templates/error/403.html`.
- **FR-008**: Hệ thống BẮT BUỘC hiển thị rõ ràng trên thanh Header Navbar: Tên người dùng đang đăng nhập, Badge màu vai trò (`DSP`, `SAL`, `MGR`) và nút Đăng xuất trực quan.
- **FR-009**: Hệ thống BẮT BUỘC tự động khởi tạo sẵn các tài khoản mẫu khi khởi động hệ thống lần đầu:
  - `dsp_user` (Mật khẩu: `password123`, Vai trò: `DSP`)
  - `sal_user` (Mật khẩu: `password123`, Vai trò: `SAL`)
  - `mgr_user` (Mật khẩu: `password123`, Vai trò: `MGR`)

### Key Entities *(include if feature involves data)*

- **User (Tài khoản người dùng)**:
  - `id`: Khóa chính định danh người dùng (Integer autoincrement)
  - `username`: Tên đăng nhập duy nhất (String 50, UNIQUE, INDEX)
  - `password_hash`: Chuỗi băm mật khẩu bảo mật bằng bcrypt (String 255, NOT NULL)
  - `full_name`: Họ và tên hiển thị của người dùng (String 100, NOT NULL)
  - `role`: Vai trò quyền hạn (`DSP`, `SAL`, `MGR`) (String 20, NOT NULL)
  - `is_active`: Trạng thái kích hoạt tài khoản (Boolean, default True)
  - `created_at`, `updated_at`: Thời điểm khởi tạo và cập nhật bản ghi

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% người dùng chưa đăng nhập khi truy cập các URL nội bộ đều bị chuyển hướng về `/login`.
- **SC-002**: Thời gian xử lý đăng nhập và xác thực phiên hoàn tất dưới 100ms.
- **SC-003**: 100% các hành vi thao tác trái quyền của tài khoản `SAL` / `MGR` trên các endpoint ghi dữ liệu bị chặn với mã HTTP 403.
- **SC-004**: Mật khẩu người dùng được bảo vệ 100% bằng chuẩn băm bcrypt; không có bất kỳ mật khẩu thô nào xuất hiện trong database hoặc log hệ thống.
- **SC-005**: Bộ test tự động (`pytest`) bao phủ 100% các kịch bản đăng nhập đúng/sai, hết phiên, phân quyền và đăng xuất đều đạt trạng thái PASS.

---

## Assumptions

- Phiên làm việc được quản lý thông qua cơ chế Session Cookie (Signed Cookie / In-Memory Session Storage) của Starlette / FastAPI, không dùng JWT cho giao diện Web SSR.
- Hệ thống tự động nạp sẵn 3 tài khoản demo phục vụ kiểm thử ngay lần chạy đầu tiên.
- Không áp dụng đăng ký tài khoản tự do từ bên ngoài; chỉ quản trị viên hoặc seed data cấp tài khoản làm việc nội bộ.
