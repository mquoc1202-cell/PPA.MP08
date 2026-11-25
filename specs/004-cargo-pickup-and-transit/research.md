# Research & Technical Decisions: TRN-03 Ghi nhận nhận hàng và vận chuyển

## 1. Cơ chế Quản lý Máy Trạng thái (State Machine Transitions)

### Bối cảnh
Theo tài liệu nghiệp vụ `03_Freight_Transportation.pdf` và ADR-002:
Vòng đời của một chuyến hàng bắt buộc phải tuân theo thứ tự tuần tự:
`UNASSIGNED` ➔ `ASSIGNED` ➔ `PICKED_UP` ➔ `IN_TRANSIT` ➔ `DELIVERED` ➔ `COMPLETED`.
Hệ thống tuyệt đối cấm nhảy cóc trạng thái (ví dụ cấm chuyển trực tiếp từ `UNASSIGNED` sang `DELIVERED`, hoặc từ `ASSIGNED` sang `IN_TRANSIT`).

### Quyết định kỹ thuật
- **Triển khai**: Đóng gói toàn bộ logic kiểm tra và chuyển đổi trạng thái trong dịch vụ chuyên biệt `TripTrackingService` (kế thừa kiến trúc từ `DispatchService`).
- **Ma trận chuyển trạng thái hợp lệ trong TRN-03**:

| Trạng thái hiện tại | Thao tác | Trạng thái đích | Điều kiện tiên quyết (Pre-conditions) |
| :--- | :--- | :--- | :--- |
| `ASSIGNED` | **Xác nhận Nhận hàng** (`record_pickup`) | `PICKED_UP` | 1. Có xe và tài xế được phân công.<br>2. `actual_cargo_weight_kg <= truck.capacity_kg`.<br>3. Xe và tài xế không có booking khác đang `IN_PROGRESS` (BR-09).<br>4. Thời điểm thực tế không ở tương lai. |
| `PICKED_UP` | **Xác nhận Khởi hành** (`record_departure`) | `IN_TRANSIT` | 1. Đang ở trạng thái `PICKED_UP`.<br>2. `actual_depart_time >= actual_pickup_time`.<br>3. Thời điểm thực tế không ở tương lai. |
| Bất kỳ trạng thái khác | Bất kỳ thao tác nào ở trên | *Bị từ chối (HTTP 400)* | Vi phạm quy tắc máy trạng thái. |

---

## 2. Đồng bộ Trạng thái Lịch trình Tài nguyên (Resource Booking Sync)

### Bối cảnh
Khi chuyến hàng ở trạng thái `ASSIGNED`, các bản ghi booking của xe và tài xế ở trạng thái `CONFIRMED`.
Khi hàng hóa được bốc lên xe và xác nhận nhận hàng (`PICKED_UP`), tài nguyên bắt đầu tham gia thực hiện nhiệm vụ thực tế ngoài đời thực.

### Quyết định kỹ thuật
- Trong phương thức `record_pickup()`, cùng với việc cập nhật trạng thái `trip.status = 'PICKED_UP'`, hệ thống thực hiện truy vấn các `ResourceBooking` có `reference_code == trip.reference_code` và cập nhật `status = 'IN_PROGRESS'`.
- Toàn bộ thao tác cập nhật Trip và Booking được gói trong một Database Transaction duy nhất (`with db.begin():`). Nếu bất kỳ bước nào lỗi, toàn bộ thay đổi bị rollback.

---

## 3. Quy tắc Kiểm tra Xung đột Thực thi (BR-09 Resource Busy Check)

### Bối cảnh
Quy tắc BR-09 trong tài liệu vận tải gốc yêu cầu: "Kiểm tra xe/tài xế đã phân công chưa đang thực hiện việc khác".
Nghĩa là tại thời điểm bấm nhận hàng, nếu xe hoặc tài xế đang dở dang thực hiện một chuyến khác (có booking ở trạng thái `IN_PROGRESS`), hệ thống phải từ chối xác nhận nhận hàng cho chuyến mới.

### Quyết định kỹ thuật
- Trước khi chuyển trạng thái sang `PICKED_UP`, `TripTrackingService` gọi `ResourceBookingRepository`:
  ```python
  busy_bookings = db.query(ResourceBooking).filter(
      ResourceBooking.resource_type.in_([ResourceType.TRUCK.value, ResourceType.DRIVER.value]),
      or_(
          and_(ResourceBooking.resource_type == ResourceType.TRUCK.value, ResourceBooking.resource_id == trip.assigned_truck_id),
          and_(ResourceBooking.resource_type == ResourceType.DRIVER.value, ResourceBooking.resource_id == trip.assigned_driver_id)
      ),
      ResourceBooking.status == BookingStatus.IN_PROGRESS.value,
      ResourceBooking.reference_code != trip.reference_code
  ).all()
  ```
- Nếu `busy_bookings` tồn tại, raise `ScheduleConflictError` hoặc `BusinessRuleViolationError`: "Xe hoặc tài xế hiện đang thực hiện chuyến hàng khác (chưa hoàn tất bàn giao), không thể xác nhận nhận hàng chuyến này."

---

## 4. Dòng thời gian Lịch sử & Nhật ký Kiểm toán (TripEvent Audit Trail)

### Bối cảnh
Yêu cầu nghiệp vụ ghi rõ: "Mỗi cập nhật lưu thời điểm thực tế và thời điểm nhập; không sửa/xóa lịch sử đã xác nhận; tra cứu công khai chỉ hiển thị phần được phép theo BR-18."

### Quyết định kỹ thuật
- Tạo bảng `trip_events` lưu vết độc lập:
  - `actual_time`: Thời điểm thực tế do tài xế/người bàn giao cung cấp.
  - `recorded_at`: Thời điểm hệ thống ghi nhận bản ghi (`datetime.now(timezone.utc)`).
  - `recorded_by_user_id`: ID của người dùng (DSP) thực hiện thao tác.
  - `event_type`: Loại sự kiện (`PICKUP_CONFIRMED`, `DEPARTURE_CONFIRMED`).
- Bảng này là bất biến (Append-only). Không có API hay giao diện nào cho phép sửa hoặc xóa các bản ghi sự kiện này.
- Khi người dùng có vai trò `SAL` hoặc `MGR` xem chi tiết chuyến, giao diện hiển thị trực quan dạng Timeline (Vertical Timeline) của Bootstrap.

---

## 5. Quy chuẩn Giao diện & Cảnh báo Tải trọng Trực quan (Frontend UX)

### Bối cảnh
Điều phối viên cần biết rõ khối lượng thực tế nhập vào có an toàn hay không ngay trước khi bấm nút Xác nhận.

### Quyết định kỹ thuật
- Trên màn hình `src/templates/trips/pickup.html`:
  - Hiển thị thẻ tóm tắt xe: Biển số, Loại xe, Tải trọng tối đa (`capacity_kg`).
  - Input `Khối lượng hàng thực tế (kg)` có gắn JavaScript lắng nghe sự kiện `input`:
    - Nếu `actual_weight > capacity_kg`: Input đổi màu viền đỏ (`is-invalid`), hiển thị thông báo cảnh báo nguy hiểm: *"VƯỢT TẢI TRỌNG XE (vượt X kg)! Hệ thống sẽ từ chối xác nhận."*, nút Submit bị vô hiệu hóa (`disabled`).
    - Nếu `actual_weight <= capacity_kg`: Input viền xanh (`is-valid`), hiển thị tải trọng an toàn và tỉ lệ chiếm dụng (ví dụ: *85% tải trọng xe*), nút Submit sẵn sàng.
    - Nếu có chênh lệch so với khối lượng dự kiến ban đầu, hiển thị trường ghi chú giải trình chênh lệch (`discrepancy_notes`).
