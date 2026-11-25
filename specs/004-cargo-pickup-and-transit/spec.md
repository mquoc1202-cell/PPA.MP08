# Feature Specification: TRN-03 Ghi nhận nhận hàng và vận chuyển (Cargo Pickup & In-Transit Tracking)

**Feature Branch**: `004-cargo-pickup-and-transit`  
**Created**: 2026-11-25  
**Status**: Draft  
**Input**: User description: "Tạo module TRN-03 Ghi nhận nhận hàng và vận chuyển theo tài liệu 03_Freight_Transportation.pdf"

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ghi nhận Nhận hàng Thực tế tại Điểm lấy hàng (Priority: P1) 🎯 MVP

Là Điều phối viên (DSP), tôi muốn ghi nhận thông tin nhận hàng thực tế từ tài xế cung cấp (thời điểm nhận, người bàn giao, mô tả tình trạng hàng hóa, khối lượng thực tế) để xác nhận chuyến hàng đã được lấy thành công và chuyển trạng thái chuyến sang `PICKED_UP`.

**Why this priority**: Đây là mốc chuyển tiếp sống còn (State Transition) đầu tiên chuyển đổi trạng thái của chuyến hàng từ đã phân công sang giai đoạn thực thi thực địa, đồng thời chuyển trạng thái booking của xe và tài xế sang `IN_PROGRESS`.

**Independent Test**:
- Tạo một chuyến hàng ở trạng thái `ASSIGNED` với xe và tài xế hợp lệ.
- Thực hiện ghi nhận nhận hàng với đầy đủ thông tin: thời điểm thực tế, người bàn giao, khối lượng thực tế hợp lệ (nhỏ hơn hoặc bằng tải trọng xe).
- Xác nhận:
  1. Trạng thái chuyến hàng chuyển thành `PICKED_UP`.
  2. Các booking của xe và tài xế chuyển thành `IN_PROGRESS`.
  3. Dữ liệu mốc nhận hàng được lưu vết với cả thời điểm thực tế và thời điểm ghi nhận hệ thống.

**Acceptance Scenarios**:

1. **Given** Chuyến hàng ở trạng thái `ASSIGNED` và tài nguyên xe/tài xế chưa bận việc khác,  
   **When** Điều phối viên gửi thông tin nhận hàng hợp lệ (thời điểm thực tế, tên người bàn giao, mô tả tình trạng hàng, khối lượng thực tế $\le$ tải trọng xe),  
   **Then** Hệ thống cập nhật trạng thái chuyến sang `PICKED_UP`, cập nhật trạng thái booking của xe và tài xế sang `IN_PROGRESS`, và hiển thị thông báo thành công.
2. **Given** Chuyến hàng đang ở trạng thái `UNASSIGNED`, `PICKED_UP`, `IN_TRANSIT`, `DELIVERED`, hoặc `COMPLETED`,  
   **When** Người dùng cố gắng thực hiện hành động nhận hàng (`PICKED_UP`),  
   **Then** Hệ thống từ chối thao tác với mã lỗi 400 và thông báo rõ ràng chỉ chuyến ở trạng thái `ASSIGNED` mới được phép ghi nhận nhận hàng.

---

### User Story 2 - Kiểm tra & Từ chối Vượt Tải trọng Thực tế tại Điểm lấy hàng (Priority: P1)

Là Điều phối viên (DSP), tôi muốn hệ thống tự động kiểm tra khối lượng hàng hóa thực tế cân tại kho so với tải trọng cho phép của xe được gán, nhằm ngăn chặn xe chở quá tải gây mất an toàn giao thông và vi phạm pháp luật.

**Why this priority**: Tuân thủ quy tắc an toàn giao thông và quy chuẩn vận tải (BR-06). Phát hiện sai lệch khối lượng tại điểm lấy hàng trước khi xe lăn bánh là yêu cầu bắt buộc của bài toán vận tải.

**Independent Test**:
- Chọn một chuyến hàng `ASSIGNED` được gán xe tải trọng 5,000 kg.
- Nhập khối lượng thực tế cân được là 5,500 kg khi nhận hàng.
- Xác nhận: Hệ thống từ chối xác nhận nhận hàng, chuyến hàng vẫn giữ nguyên trạng thái `ASSIGNED`, booking vẫn ở trạng thái `CONFIRMED` (không bị chuyển sang `IN_PROGRESS`), và giao diện cảnh báo lỗi vượt tải trọng chi tiết.

**Acceptance Scenarios**:

1. **Given** Xe được phân công có tải trọng 5,000 kg,  
   **When** Điều phối viên nhập khối lượng hàng thực tế là 5,200 kg khi xác nhận nhận hàng,  
   **Then** Hệ thống từ chối thao tác, giữ nguyên trạng thái chuyến hàng là `ASSIGNED`, không chuyển booking sang `IN_PROGRESS`, và yêu cầu điều phối viên đổi nguồn lực xe lớn hơn hoặc làm việc lại với bên kinh doanh.
2. **Given** Khối lượng hàng thực tế có chênh lệch so với khối lượng dự kiến ban đầu nhưng vẫn $\le$ tải trọng xe,  
   **When** Điều phối viên xác nhận nhận hàng kèm ghi chú giải trình chênh lệch,  
   **Then** Hệ thống chấp nhận cập nhật khối lượng thực tế và chuyển trạng thái sang `PICKED_UP` bình thường.

---

### User Story 3 - Kiểm tra Xung đột Thực thi Nguồn lực theo Quy tắc BR-09 (Priority: P2)

Là Điều phối viên (DSP), tôi muốn hệ thống kiểm tra và ngăn chặn việc ghi nhận nhận hàng nếu xe tải hoặc tài xế được phân công đang dở dang thực hiện một chuyến hàng khác (đang ở trạng thái `IN_PROGRESS`), nhằm đảm bảo một nguồn lực không thể có mặt ở 2 nơi cùng lúc.

**Why this priority**: Tuân thủ quy tắc nghiệp vụ BR-09 trong tài liệu vận tải gốc, đảm bảo tính toàn vẹn về mặt không gian và thời gian của phương tiện và con người ngoài thực tế.

**Independent Test**:
- Gán Xe A và Tài xế B cho Chuyến 1 (đang ở trạng thái `IN_PROGRESS`).
- Chuyến 2 cũng được phân công Xe A hoặc Tài xế B (ở trạng thái `ASSIGNED`).
- Thao tác xác nhận nhận hàng cho Chuyến 2.
- Xác nhận: Hệ thống phát hiện xung đột bận việc khác và từ chối xác nhận nhận hàng cho Chuyến 2 cho đến khi Chuyến 1 kết thúc.

**Acceptance Scenarios**:

1. **Given** Xe tải hoặc tài xế của chuyến hàng đang có một booking khác ở trạng thái `IN_PROGRESS`,  
   **When** Điều phối viên xác nhận nhận hàng (`PICKED_UP`) cho chuyến hàng hiện tại,  
   **Then** Hệ thống từ chối với thông báo lỗi xung đột nguồn lực đang thực hiện nhiệm vụ khác (BR-09), giữ nguyên trạng thái `ASSIGNED`.

---

### User Story 4 - Ghi nhận Khởi hành và Chuyển trạng thái Đang vận chuyển (`IN_TRANSIT`) (Priority: P2)

Là Điều phối viên (DSP), tôi muốn ghi nhận mốc thời gian xe bắt đầu lăn bánh rời điểm lấy hàng để chuyển trạng thái chuyến hàng sang `IN_TRANSIT` (Đang vận chuyển), giúp khách hàng và bộ phận kinh doanh nắm được xe đang trên đường giao.

**Why this priority**: Hoàn thiện mắt xích tiếp theo của máy trạng thái (State Machine), đảm bảo tính liên tục của hành trình và tuyệt đối chống nhảy cóc trạng thái (ADR-002).

**Independent Test**:
- Chuyến hàng ở trạng thái `PICKED_UP`.
- Nhập thời điểm khởi hành thực tế (`actual_depart_time`).
- Xác nhận trạng thái chuyển sang `IN_TRANSIT`.
- Kiểm tra cố gắng chuyển từ `ASSIGNED` hoặc `UNASSIGNED` sang `IN_TRANSIT` trực tiếp sẽ bị chặn ngay lập tức.

**Acceptance Scenarios**:

1. **Given** Chuyến hàng đang ở trạng thái `PICKED_UP`,  
   **When** Điều phối viên gửi xác nhận xe khởi hành với thời điểm xuất phát thực tế,  
   **Then** Hệ thống cập nhật trạng thái chuyến sang `IN_TRANSIT` và ghi nhận mốc thời gian khởi hành.
2. **Given** Chuyến hàng đang ở trạng thái `ASSIGNED` hoặc `UNASSIGNED`,  
   **When** Người dùng cố gắng gọi lệnh chuyển trạng thái sang `IN_TRANSIT` hoặc `DELIVERED`,  
   **Then** Hệ thống chặn thao tác (mã lỗi 400), khẳng định quy tắc không được nhảy cóc trạng thái (bắt buộc phải qua `PICKED_UP`).

---

### User Story 5 - Dòng thời gian Lịch sử & Phân quyền Tra cứu Tiến độ (Priority: P3)

Là Người dùng (Kinh doanh SAL hoặc Quản lý MGR), tôi muốn theo dõi dòng thời gian (Timeline) các mốc vận chuyển của chuyến hàng (thời gian nhận, người bàn giao, tình trạng hàng, thời gian khởi hành) dưới chế độ chỉ đọc mà không có quyền thay đổi dữ liệu, tuân thủ quy tắc bảo mật BR-18.

**Why this priority**: Cung cấp khả năng hiển thị (Observability) và minh bạch tiến độ cho các bộ phận liên quan mà vẫn duy trì kiểm soát truy cập nghiêm ngặt theo vai trò (RBAC).

**Independent Test**:
- Đăng nhập bằng tài khoản `sal` hoặc `mgr`.
- Truy cập chi tiết chuyến hàng: xem được timeline đầy đủ.
- Gửi yêu cầu cập nhật `PICKED_UP` hoặc `IN_TRANSIT` dưới quyền `sal`: nhận mã lỗi 403 Forbidden.

**Acceptance Scenarios**:

1. **Given** Người dùng có vai trò `SAL` hoặc `MGR`,  
   **When** Xem chi tiết chuyến hàng tại giao diện web hoặc gọi API tra cứu,  
   **Then** Hệ thống hiển thị dòng thời gian trực quan gồm các mốc thời gian thực tế và thông tin bàn giao, nhưng ẩn hoặc vô hiệu hóa các nút cập nhật trạng thái.
2. **Given** Người dùng có vai trò `SAL` hoặc `MGR`,  
   **When** Cố gắng gọi API POST cập nhật mốc nhận hàng hoặc khởi hành,  
   **Then** Hệ thống trả về mã lỗi HTTP 403 Forbidden và từ chối ghi nhận.

---

### Edge Cases

- **Khối lượng thực tế bằng đúng tải trọng xe**: Hệ thống cho phép nhận hàng bình thường (ngưỡng $\le$ tải trọng).
- **Khối lượng thực tế không xác định hoặc $\le 0$**: Hệ thống từ chối với thông báo lỗi validation bắt buộc khối lượng phải là số nguyên dương.
- **Thời điểm thực tế nhận hàng trong tương lai**: Hệ thống từ chối nếu thời điểm nhận hàng thực tế được nhập lớn hơn thời điểm hiện tại của máy chủ.
- **Thời điểm khởi hành trước thời điểm nhận hàng**: Hệ thống từ chối nếu thời điểm khởi hành (`actual_depart_time`) xảy ra trước thời điểm nhận hàng (`actual_pickup_time`).
- **Ghi nhận trùng lặp (Double Submission)**: Nếu điều phối viên vô tình bấm nút xác nhận nhận hàng hai lần liên tiếp, giao dịch thứ hai phát hiện trạng thái đã là `PICKED_UP` và từ chối an toàn mà không làm hỏng dữ liệu hay nhân đôi sự kiện mốc.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống BẮT BUỘC chỉ cho phép chuyển trạng thái chuyến hàng sang `PICKED_UP` khi trạng thái hiện tại là `ASSIGNED`.
- **FR-002**: Khi ghi nhận nhận hàng (`PICKED_UP`), hệ thống BẮT BUỘC thu thập các thông tin:
  - Thời điểm nhận hàng thực tế (`actual_pickup_time`).
  - Họ tên người bàn giao hàng phía kho gửi (`handover_person`).
  - Khối lượng hàng thực tế cân được (`actual_cargo_weight_kg`).
  - Mô tả tình trạng bao bì / quy cách hàng hóa (`cargo_condition`).
  - Ghi chú sai lệch (nếu có chênh lệch khối lượng/số lượng) (`discrepancy_notes`).
- **FR-003**: Hệ thống BẮT BUỘC kiểm tra điều kiện tải trọng: nếu `actual_cargo_weight_kg > truck.capacity_kg`, hệ thống PHẢI từ chối xác nhận nhận hàng và giữ nguyên chuyến hàng ở trạng thái `ASSIGNED`.
- **FR-004**: Khi nhận hàng thành công, hệ thống BẮT BUỘC chuyển trạng thái của 2 booking tương ứng (xe và tài xế) từ `CONFIRMED` sang `IN_PROGRESS`.
- **FR-005**: Hệ thống BẮT BUỘC kiểm tra quy tắc BR-09: từ chối nhận hàng nếu xe hoặc tài xế được phân công đang có một booking khác ở trạng thái `IN_PROGRESS`.
- **FR-006**: Hệ thống BẮT BUỘC chỉ cho phép chuyển trạng thái chuyến hàng sang `IN_TRANSIT` khi trạng thái hiện tại là `PICKED_UP`.
- **FR-007**: Khi chuyển trạng thái sang `IN_TRANSIT`, hệ thống BẮT BUỘC ghi nhận thời điểm khởi hành thực tế (`actual_depart_time`), và thời điểm này không được diễn ra trước thời điểm nhận hàng (`actual_pickup_time`).
- **FR-008**: Hệ thống BẮT BUỘC ghi nhận kép cả hai mốc thời gian cho mọi sự kiện chuyển trạng thái:
  - Thời điểm thực tế diễn ra sự kiện do tài xế/kho cung cấp (`actual_time`).
  - Thời điểm ghi nhận vào hệ thống (`recorded_at` / hệ thống tự sinh).
- **FR-009**: Hệ thống BẮT BUỘC cấm nhảy cóc trạng thái (State Machine Guard):
  - Cấm `UNASSIGNED` ➔ `PICKED_UP` hoặc `IN_TRANSIT` hoặc `DELIVERED`.
  - Cấm `ASSIGNED` ➔ `IN_TRANSIT` hoặc `DELIVERED`.
- **FR-010**: Hệ thống BẮT BUỘC bảo vệ quyền ghi: chỉ người dùng có vai trò `DSP` (Điều phối viên) mới được phép cập nhật mốc nhận hàng và khởi hành. Vai trò `SAL` và `MGR` chỉ có quyền tra cứu (trả về 403 nếu ghi).

---

### Key Entities *(include if feature involves data)*

- **Trip (Chuyến hàng - Mở rộng)**:
  - Bổ sung các thuộc tính theo dõi mốc:
    - `actual_cargo_weight_kg`: Khối lượng thực tế ghi nhận lúc nhận hàng (INTEGER, NULLABLE, CHECK > 0).
    - `handover_person`: Người bàn giao hàng tại kho nhận (VARCHAR(100), NULLABLE).
    - `cargo_condition`: Tình trạng hàng hóa/bao bì (VARCHAR(255), NULLABLE).
    - `discrepancy_notes`: Ghi chú sai lệch (VARCHAR(500), NULLABLE).
    - `actual_pickup_time`: Thời điểm nhận hàng thực tế (DATETIME, NULLABLE).
    - `actual_depart_time`: Thời điểm xe bắt đầu di chuyển (DATETIME, NULLABLE).
    - `pickup_recorded_at`: Thời điểm nhập thông tin nhận hàng vào hệ thống (DATETIME, NULLABLE).
    - `depart_recorded_at`: Thời điểm nhập thông tin khởi hành vào hệ thống (DATETIME, NULLABLE).
- **TripEvent / AuditTimeline (Sự kiện Mốc Chuyến hàng)**:
  - Ghi nhận chi tiết từng bước chuyển trạng thái phục vụ hiển thị Timeline và đối soát lịch sử:
    - `id`: Định danh duy nhất.
    - `trip_id`: Liên kết tới chuyến hàng.
    - `event_type`: Loại sự kiện (`PICKUP_CONFIRMED`, `DEPARTURE_CONFIRMED`).
    - `from_status`: Trạng thái trước khi chuyển (`ASSIGNED`, `PICKED_UP`).
    - `to_status`: Trạng thái sau khi chuyển (`PICKED_UP`, `IN_TRANSIT`).
    - `actual_time`: Thời điểm thực tế diễn ra.
    - `recorded_at`: Thời điểm hệ thống ghi nhận.
    - `recorded_by_user_id`: Người dùng thực hiện thao tác.
    - `notes`: Ghi chú bổ sung hoặc lý do sai lệch.
- **ResourceBooking (Lịch trình Nguồn lực)**:
  - Chuyển `status` từ `CONFIRMED` ➔ `IN_PROGRESS` khi chuyến sang `PICKED_UP`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các chuyến hàng được xác nhận nhận hàng (`PICKED_UP`) đều có đầy đủ thông tin: người bàn giao, tình trạng hàng và khối lượng thực tế.
- **SC-002**: 100% các trường hợp khối lượng thực tế vượt tải trọng xe bị chặn tự động ngay tại thời điểm nhập, bảo toàn chuyến ở trạng thái `ASSIGNED` và không gây vượt tải trọng.
- **SC-003**: 0% trường hợp nhảy cóc trạng thái (ví dụ từ `ASSIGNED` nhảy thẳng sang `IN_TRANSIT` hay `DELIVERED`), bảo đảm quy trình vận hành tuần tự không lỗi lọt.
- **SC-004**: Thời gian điều phối viên hoàn tất thao tác ghi nhận nhận hàng trên giao diện web dưới 30 giây với giao diện hiển thị cảnh báo trực quan tải trọng.
- **SC-005**: 100% các thao tác cập nhật mốc nhận hàng và khởi hành đều lưu vết chuẩn xác cả thời điểm thực tế và thời điểm ghi nhận hệ thống.

---

## Assumptions

- **Thông tin từ tài xế**: Điều phối viên nhận thông tin mốc nhận hàng qua điện thoại, tin nhắn hoặc ứng dụng liên lạc của tài xế và nhập trực tiếp vào cổng thông tin Freight ERP.
- **Quy chuẩn tải trọng**: Khối lượng hàng hóa thực tế được xác định theo phiếu cân kho hoặc phiếu bàn giao hàng hóa tại địa điểm nhận.
- **Không tự động sinh vị trí GPS**: Tuân thủ ghi chú trong tài liệu `03_Freight_Transportation.pdf`: "Hệ thống không tự suy diễn vị trí GPS hoặc trạng thái giao từ thời gian dự kiến; trạng thái chỉ đổi theo sự kiện nghiệp vụ đã được ghi nhận."
- **Quyền hạn vai trò**: Chỉ vai trò `DSP` được phép cập nhật mốc nghiệp vụ. Mọi truy cập cập nhật từ `SAL` hoặc `MGR` bị chặn ở tầng Authorization với mã HTTP 403.
