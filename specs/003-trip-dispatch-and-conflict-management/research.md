# Research & Technical Decisions: 003-trip-dispatch-and-conflict-management

**Feature**: `003-trip-dispatch-and-conflict-management` (TRN-02)  
**Date**: 2026-11-23  
**Status**: Completed  
**Reference**: `03_Freight_Transportation.pdf`, `.specify/memory/constitution.md`  

---

## 1. Cơ chế Kiểm soát Xung đột Trùng lịch Nguồn lực (Resource Schedule Overlap Detection)

### Vấn đề cần giải quyết
Theo quy tắc nghiệp vụ BR-07 và BR-08, xe và tài xế không được phép trùng lịch với bất kỳ lịch trình vận tải hoặc thuê xe nào khác trong khoảng thời gian `[start_time, end_time]`. Nếu xảy ra trùng lịch, hệ thống phải từ chối ngay lập tức và tuyệt đối không tạo lịch chiếm dụng một phần (partial booking).

### Quyết định kỹ thuật
- **Công thức phát hiện giao thoa thời gian (Time Interval Overlap Formula)**:
  Hai khoảng thời gian $[S_1, E_1]$ và $[S_2, E_2]$ giao nhau khi và chỉ khi:
  $$S_1 < E_2 \quad \text{VÀ} \quad E_1 > S_2$$
- Áp dụng truy vấn SQLAlchemy:
  ```python
  query = db.query(ResourceBooking).filter(
      ResourceBooking.resource_type == resource_type,
      ResourceBooking.resource_id == resource_id,
      ResourceBooking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.IN_PROGRESS.value]),
      ResourceBooking.start_time < new_end_time,
      ResourceBooking.end_time > new_start_time
  )
  if exclude_reference_code:
      query = query.filter(ResourceBooking.reference_code != exclude_reference_code)
  ```
- **Hỗ trợ đa dịch vụ**: Bảng `resource_bookings` lưu trữ cả đơn vận tải (`FREIGHT`) và hợp đồng thuê xe (`RENTAL`), đảm bảo việc kiểm tra bao quát 100% mọi nguồn phát sinh chiếm dụng.
- **Lý do chọn**: Công thức chuẩn đại số quan hệ, phát hiện chính xác mọi trường hợp: bao trùm hoàn toàn, chồng lấn một phần đầu, một phần đuôi, hoặc nằm gọn bên trong.

---

## 2. Quản lý Giao dịch & Kiểm soát Đồng thời (ACID Transaction & Concurrency Locking)

### Vấn đề cần giải quyết
Theo Hiến pháp dự án (`constitution.md - Nguyên tắc III`) và tài liệu TRN-02:
"Khi 2 điều phối viên cùng lúc giữ một xe/tài xế trong lịch chồng, chỉ duy nhất một thao tác thành công; người còn lại được thông báo kiểm tra lại lịch. Từ chối thì không tạo booking một phần."

### Quyết định kỹ thuật
- **Giao dịch nguyên tử (Atomic Transaction)**:
  Toàn bộ quá trình phân công gồm:
  1. Khóa/Kiểm tra trạng thái chuyến hàng (`Trip.status == 'UNASSIGNED'`).
  2. Kiểm tra tải trọng xe (`capacity_kg >= cargo_weight_kg`).
  3. Kiểm tra tính sẵn sàng của xe và tài xế (`status == 'ACTIVE'`).
  4. Kiểm tra xung đột trùng lịch của xe.
  5. Kiểm tra xung đột trùng lịch của tài xế.
  6. Tạo 2 bản ghi `ResourceBooking` (Xe & Tài xế).
  7. Cập nhật trạng thái chuyến sang `ASSIGNED`.
  Bọc toàn bộ trong một transaction `with db.begin():` (hoặc `db.commit()` có `try...except rollback()`). Bất kỳ điều kiện nào không thỏa mãn sẽ kích hoạt rollback 100%.
- **Chống Race Condition giữa 2 điều phối viên**:
  - Khi bắt đầu kiểm tra và phân công, thực hiện khóa ở mức database hoặc sử dụng SQLite transaction isolation `BEGIN IMMEDIATE` / `with_for_update()` trên các bản ghi nguồn lực liên quan.
  - Sau khi kiểm tra overlap, lập tức chèn 2 bản ghi booking và commit. Nếu điều phối viên thứ 2 đọc sau, truy vấn overlap sẽ ngay lập tức phát hiện booking vừa tạo và ném ngoại lệ `ScheduleConflictError` (HTTP 409).
- **Lý do chọn**: Đảm bảo tuân thủ nghiêm ngặt chuẩn ACID, loại bỏ hoàn toàn khả năng 1 xe hoặc 1 tài xế bị gán trùng vào cùng một khung giờ.

---

## 3. Máy Trạng thái Chuyến hàng & Ràng buộc Thay đổi Phân công (State Machine Guardrails)

### Vấn đề cần giải quyết
Theo tài liệu TRN-02:
"Chỉ được đổi hoặc gỡ phân công trước PICKED_UP. Đổi thành công giải phóng lịch cũ và giữ lịch mới nhất quán; đổi thất bại giữ nguyên phân công cũ."

### Quyết định kỹ thuật
- **Điều kiện cho phép can thiệp phân công**:
  - `assign_trip`: Chỉ áp dụng cho chuyến có trạng thái `UNASSIGNED`.
  - `reassign_trip` / `unassign_trip`: Chỉ áp dụng khi chuyến có trạng thái `ASSIGNED`.
  - Nếu chuyến đã chuyển sang `PICKED_UP`, `IN_TRANSIT`, `DELIVERED`, `COMPLETED` ➔ Ném ngoại lệ `BusinessRuleViolationError("Chuyến hàng đã bắt đầu thực hiện hoặc hoàn tất, không được phép thay đổi phân công.")`.
- **Cơ chế Đổi phân công an toàn (Atomic Swap)**:
  - Khi đổi xe hoặc tài xế mới: Kiểm tra tải trọng và trùng lịch của nguồn lực mới (bỏ qua booking của chính chuyến này qua `exclude_reference_code`).
  - Nếu nguồn lực mới hợp lệ:
    - Hủy/giải phóng các booking cũ (`BookingStatus.CANCELLED` hoặc xóa an toàn).
    - Tạo các booking mới cho nguồn lực mới.
    - Cập nhật chuyến hàng.
  - Nếu nguồn lực mới bị lỗi (ví dụ tài xế mới trùng lịch):
    - Toàn bộ transaction bị hủy, các booking cũ và phân công cũ được **giữ nguyên vẹn 100%**.
- **Cơ chế Gỡ phân công (Unassign)**:
  - Giải phóng toàn bộ booking của chuyến.
  - Đưa `assigned_truck_id = None`, `assigned_driver_id = None`.
  - Chuyển trạng thái chuyến về lại `UNASSIGNED`.

---

## 4. Kiến trúc Giao diện & Trải nghiệm Người dùng (UI/UX)

### Quyết định kỹ thuật
1. **Trang Danh sách Chuyến hàng (`/trips`)**:
   - Hiển thị danh sách các chuyến hàng phân loại theo Tabs: `Tất cả`, `Chưa phân công (UNASSIGNED)`, `Đã phân công (ASSIGNED)`, `Đang vận chuyển`, `Đã giao hàng`.
   - Nút thao tác nhanh: `Điều phối` (đối với chuyến `UNASSIGNED`), `Đổi xe/tài xế` và `Hủy gán` (đối với chuyến `ASSIGNED`).
2. **Màn hình Điều phối Chuyến (`/trips/{id}/dispatch`)**:
   - Hiển thị tóm tắt thông tin đơn hàng: Mã đơn, Khối lượng hàng, Điểm lấy/giao hàng, Ghi chú.
   - Form chọn Xe: Dropdown hiển thị biển số, loại xe, tải trọng tối đa, kèm chỉ báo tự động xanh/đỏ nếu xe đủ tải hoặc thiếu tải.
   - Form chọn Tài xế: Dropdown hiển thị mã tài xế, họ tên, số điện thoại.
   - Chọn khung thời gian chiếm dụng dự kiến: `estimated_start_time` và `estimated_end_time`.
3. **Modal Cảnh báo Xung đột Lịch trình (HTTP 409)**:
   - Khi có xung đột lịch hoặc lỗi nghiệp vụ, hiển thị Modal cảnh báo chi tiết theo quy chuẩn `AGENTS.md` (mã đơn xung đột, thời gian bắt đầu, thời gian kết thúc) và giữ nguyên form để điều phối viên chọn nguồn lực khác.
4. **Màn hình Tra cứu Lịch Nguồn lực (`/schedule`)**:
   - Xem lịch bận của Xe và Tài xế dạng danh sách theo ngày/tuần, phục vụ tra cứu nhanh trước khi điều phối.
