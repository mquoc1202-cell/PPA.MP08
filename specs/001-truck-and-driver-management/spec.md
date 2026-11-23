# Feature Specification: TRN-01 Quản lý xe và tài xế

**Feature Branch**: `001-truck-and-driver-management`

**Created**: 2026-11-23

**Status**: Draft

**Input**: User description: "Tạo module TRN-01 Quản lý xe và tài xế theo tài liệu 03_Freight_Transportation.pdf"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Quản lý và thiết lập danh mục Xe (Priority: P1)

Là điều phối viên (DSP), tôi muốn tạo mới và cập nhật thông tin đội xe để biết nguồn lực phương tiện sẵn sàng phục vụ các đơn vận tải.

**Why this priority**: Xe là phương tiện cốt lõi để thực hiện vận chuyển. Nếu không có dữ liệu xe đã được xác thực biển số và tải trọng, hệ thống không thể thực hiện bất kỳ chuyến hàng nào.

**Independent Test**: Có thể kiểm thử độc lập bằng cách tạo mới xe, cập nhật thông tin xe, thử tạo biển số trùng lặp sau chuẩn hóa hoặc tải trọng âm/bằng 0 và xác minh hệ thống từ chối theo đúng tiêu chí.

**Acceptance Scenarios**:

1. **Given** thông tin xe hợp lệ (Biển số: `29C-123.45`, loại xe: `Xe tải 5 tấn`, tải trọng: `5000` kg, trạng thái ban đầu: `ACTIVE`), **When** điều phối viên gửi yêu cầu tạo xe, **Then** hệ thống lưu thành công xe với biển số đã chuẩn hóa (`29C12345`) và tải trọng dương.
2. **Given** trong hệ thống đã tồn tại xe biển số `29C-123.45`, **When** điều phối viên tạo xe mới với biển số `29c 12345` hoặc `29C - 123.45`, **Then** hệ thống chuẩn hóa (in hoa, bỏ khoảng trắng và dấu phân cách) và từ chối do trùng lặp biển số.
3. **Given** thông tin xe có tải trọng `<= 0` kg, **When** gửi yêu cầu tạo hoặc sửa, **Then** hệ thống báo lỗi và không lưu bản ghi.

---

### User Story 2 - Quản lý và thiết lập danh mục Tài xế (Priority: P1)

Là điều phối viên (DSP), tôi muốn tạo mới và quản lý danh sách tài xế để phân bổ nhân lực vận hành chuyến hàng.

**Why this priority**: Tài xế là nhân sự bắt buộc gắn liền với chuyến xe. Cần có hồ sơ tài xế chuẩn xác trước khi điều phối.

**Independent Test**: Có thể kiểm thử độc lập bằng cách tạo tài xế mới với mã, họ tên, số điện thoại, cập nhật trạng thái `ACTIVE / INACTIVE`.

**Acceptance Scenarios**:

1. **Given** thông tin tài xế hợp lệ (Mã: `TX001`, Tên: `Nguyễn Văn A`, SĐT: `0912345678`, trạng thái: `ACTIVE`), **When** tạo mới, **Then** hệ thống lưu tài xế thành công.
2. **Given** tài xế đã tồn tại mã `TX001`, **When** tạo mới tài xế khác với mã trùng `TX001`, **Then** hệ thống từ chối do trùng mã tài xế.

---

### User Story 3 - Bảo toàn lịch sử & Khóa xóa cứng (Soft Delete) (Priority: P2)

Là người quản trị và kiểm toán hệ thống, tôi muốn đảm bảo các xe và tài xế đã từng phát sinh giao dịch/chuyến hàng không thể bị xóa khỏi hệ thống để bảo toàn lịch sử dữ liệu.

**Why this priority**: Tuân thủ nguyên tắc Immutable Audit Trail trong Hiến pháp dự án và tiêu chí chấp nhận TRN-01.

**Independent Test**: Gán xe/tài xế vào một đơn hàng/booking, sau đó gửi yêu cầu xóa và xác minh hệ thống từ chối xóa cứng, chỉ cho phép chuyển sang `INACTIVE`.

**Acceptance Scenarios**:

1. **Given** xe hoặc tài xế đã từng có booking hoặc chuyến hàng liên kết, **When** người dùng thao tác xóa, **Then** hệ thống ngăn chặn hành vi xóa cứng khỏi CSDL, hiển thị thông báo chỉ được phép chuyển trạng thái ngừng hoạt động.
2. **Given** xe hoặc tài xế chưa từng phát sinh bất kỳ giao dịch nào, **When** yêu cầu xóa, **Then** hệ thống cho phép xóa hoặc chuyển trạng thái tùy theo chính sách.

---

### User Story 4 - Ràng buộc chuyển trạng thái & Kiểm tra lịch tương lai (Priority: P2)

Là điều phối viên, tôi muốn khi chuyển xe sang `MAINTENANCE` hoặc `INACTIVE`, và tài xế sang `INACTIVE`, hệ thống phải kiểm tra xem họ có lịch điều phối trong tương lai hay không để không làm gián đoạn vận hành.

**Why this priority**: Ngăn ngừa tình trạng xe hỏng hoặc tài xế nghỉ việc đột xuất nhưng vẫn còn các cuốc hàng đã phân công mà không được xử lý điều phối lại.

**Independent Test**: Tạo một lịch booking tương lai cho xe A, cố tình đổi trạng thái xe A sang `MAINTENANCE`, kiểm tra hệ thống liệt kê các lịch bị ảnh hưởng và chặn hoàn tất đổi trạng thái cho đến khi gỡ/đổi phân công.

**Acceptance Scenarios**:

1. **Given** xe hoặc tài xế đang có lịch phân công trong tương lai, **When** điều phối viên đổi trạng thái sang không sẵn sàng (`MAINTENANCE` hoặc `INACTIVE`), **Then** hệ thống hiển thị danh sách các lịch cần xử lý và KHÔNG cho phép hoàn tất thay đổi trước khi gỡ hoặc đổi phân công đó.
2. **Given** xe hoặc tài xế đang trong chuyến hàng thực tế (`PICKED_UP` hoặc `IN_TRANSIT`), **When** cố tình đổi trạng thái sang `INACTIVE`, **Then** hệ thống từ chối để tránh bỏ qua quy trình kết thúc cuốc xe chuẩn.
3. **Given** xe ở trạng thái `MAINTENANCE/INACTIVE` hoặc tài xế ở trạng thái `INACTIVE`, **When** điều phối viên mở danh sách chọn nguồn lực cho chuyến mới, **Then** hệ thống không hiển thị các nguồn lực này; nếu gửi mã trực tiếp qua API, backend bắt buộc từ chối.

---

### Edge Cases

- **Biển số xe có định dạng lạ hoặc dấu gạch nối phức tạp:** Ví dụ `29-C1 - 123.45` so với `29C112345`. Hệ thống phải chuẩn hóa bằng Regex: loại bỏ toàn bộ khoảng trắng, dấu gạch nối, dấu chấm và chuyển hoa (`toUpperCase()`) trước khi kiểm tra trùng.
- **Tải trọng xe là số thập phân hoặc số 0:** Tải trọng bắt buộc là số nguyên hoặc số thực dương (`kg > 0`). Không chấp nhận tải trọng bằng 0 hoặc âm.
- **Tài xế có số điện thoại không hợp lệ:** Số điện thoại phải đúng định dạng liên lạc chuẩn (10 chữ số).
- **Cùng lúc đổi trạng thái xe khi có điều phối viên khác vừa gán lịch:** Phải áp dụng kiểm tra tại thời điểm commit transaction đổi trạng thái.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống BẮT BUỘC cho phép tạo mới và chỉnh sửa thông tin xe bao gồm: Biển số xe, Loại xe, Tải trọng (kg), Mô tả, và Trạng thái (`ACTIVE`, `MAINTENANCE`, `INACTIVE`).
- **FR-002**: Hệ thống BẮT BUỘC chuẩn hóa biển số xe (viết hoa toàn bộ, xóa khoảng trắng, xóa dấu phân cách như `-`, `.`) trước khi lưu và kiểm tra trùng lặp duy nhất.
- **FR-003**: Hệ thống BẮT BUỘC xác thực tải trọng xe phải là số dương (`> 0`).
- **FR-004**: Hệ thống BẮT BUỘC cho phép tạo mới và chỉnh sửa thông tin tài xế bao gồm: Mã tài xế (duy nhất), Họ tên, Số điện thoại, và Trạng thái (`ACTIVE`, `INACTIVE`).
- **FR-005**: Hệ thống BẮT BUỘC cấm xóa cứng (Hard Delete) bất kỳ xe hoặc tài xế nào đã có lịch sử tham gia giao dịch hoặc cuốc vận tải.
- **FR-006**: Khi chuyển xe/tài xế sang trạng thái không sẵn sàng (`MAINTENANCE` hoặc `INACTIVE`), hệ thống BẮT BUỘC kiểm tra lịch trong tương lai. Nếu còn lịch, hệ thống PHẢI liệt kê các lịch bị ảnh hưởng và CHẶN cập nhật cho đến khi các phân công được gỡ/đổi.
- **FR-007**: Hệ thống BẮT BUỘC ngăn cấm chuyển nguồn lực đang trong chuyến thực hiện (`IN_PROGRESS` / `IN_TRANSIT`) sang `INACTIVE` nhằm bỏ qua quy trình kết thúc cuốc xe.
- **FR-008**: Backend BẮT BUỘC từ chối việc chọn xe `MAINTENANCE/INACTIVE` hoặc tài xế `INACTIVE` cho các lượt phân công mới, ngay cả khi API nhận mã trực tiếp từ client.
- **FR-009**: Lịch rảnh/bận của xe và tài xế BẮT BUỘC phải được tính toán tự động dựa trên booking và việc sử dụng thực tế từ các chuyến xe; hệ thống TUYỆT ĐỐI KHÔNG hỗ trợ nhập tay đè lên lịch.

### Key Entities *(include if feature involves data)*

- **Truck (Xe)**:
  - `id`: Định danh duy nhất (UUID hoặc Integer PK)
  - `plate_number`: Biển số hiển thị gốc (ví dụ: `29C-123.45`)
  - `normalized_plate`: Biển số đã chuẩn hóa để đánh Unique Index (ví dụ: `29C12345`)
  - `truck_type`: Loại xe (xe tải, xe thùng kín, xe bạt...)
  - `capacity_kg`: Tải trọng tối đa tính bằng kg (`> 0`)
  - `description`: Mô tả chi tiết
  - `status`: Trạng thái (`ACTIVE`, `MAINTENANCE`, `INACTIVE`)
  - `created_at`, `updated_at`: Thời gian khởi tạo và cập nhật
- **Driver (Tài xế)**:
  - `id`: Định danh duy nhất
  - `driver_code`: Mã tài xế (Unique)
  - `full_name`: Họ và tên tài xế
  - `phone_number`: Số điện thoại liên hệ
  - `status`: Trạng thái (`ACTIVE`, `INACTIVE`)
  - `created_at`, `updated_at`: Thời gian khởi tạo và cập nhật
- **ResourceBooking (Lịch chiếm dụng nguồn lực)**:
  - Bảng liên kết lưu vết lịch trình của xe và tài xế gắn liền với mã chuyến vận tải hoặc đơn thuê xe, dùng để tính toán lịch rảnh/bận tự động.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% biển số xe trùng sau chuẩn hóa (viết hoa, không khoảng trắng, không dấu chấm/gạch) bị phát hiện và từ chối lưu.
- **SC-002**: 100% yêu cầu xóa cứng xe/tài xế đã có dữ liệu giao dịch bị chặn; toàn bộ dữ liệu lịch sử được giữ nguyên trạng.
- **SC-003**: 100% trường hợp xe/tài xế còn lịch trong tương lai cố tình chuyển sang `INACTIVE` bị chặn và hiển thị rõ ràng danh sách booking xung đột cần xử lý.
- **SC-004**: Bộ test tự động (`pytest`) bao phủ 100% các Acceptance Scenarios của cả 4 User Stories đạt trạng thái PASS.

---

## Assumptions

- Điều phối viên (`DSP`) là vai trò duy nhất có quyền tạo, sửa và đổi trạng thái xe và tài xế.
- Dữ liệu lịch rảnh/bận là thuộc tính tính toán động (`computed property`) từ bảng Booking/Trips, không lưu cờ rảnh/bận tĩnh trong bảng Truck/Driver.
- Giao diện web được dựng bằng Jinja2 Templates kết hợp Bootstrap 5, và các API tương ứng trả JSON chuẩn `{success, data, error, meta}`.
