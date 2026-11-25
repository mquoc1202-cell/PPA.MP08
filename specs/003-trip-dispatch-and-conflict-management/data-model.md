# Data Model Specification: 003-trip-dispatch-and-conflict-management

**Feature**: `003-trip-dispatch-and-conflict-management` (TRN-02)  
**Date**: 2026-11-23  
**Status**: Completed  
**Reference**: `03_Freight_Transportation.pdf`, `.specify/memory/constitution.md`  

---

## 1. Thực thể (Entities) & Thuộc tính

### 1.1. Bảng `trips` (Danh mục Chuyến Hàng)

Lưu trữ thông tin chi tiết từng chuyến hàng, thông tin hàng hóa, lịch trình điều phối dự kiến và liên kết nguồn lực được phân công.

| Tên trường | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Khóa chính định danh chuyến hàng |
| `reference_code` | `VARCHAR(50)` | `NOT NULL, UNIQUE, INDEX` | Mã chuyến hàng duy nhất (ví dụ: `TRIP-2026-001`) |
| `sender_name` | `VARCHAR(100)` | `NOT NULL` | Họ tên người gửi hàng |
| `sender_phone` | `VARCHAR(20)` | `NOT NULL` | Số điện thoại liên hệ người gửi |
| `pickup_address` | `VARCHAR(255)` | `NOT NULL` | Địa chỉ điểm lấy hàng |
| `delivery_address` | `VARCHAR(255)` | `NOT NULL` | Địa chỉ điểm giao hàng |
| `cargo_weight_kg` | `INTEGER` | `NOT NULL, CHECK (cargo_weight_kg > 0)` | Khối lượng hàng hóa (kg) |
| `cargo_type` | `VARCHAR(100)` | `NOT NULL` | Mô tả loại hàng hóa (hàng khô, điện tử, đông lạnh...) |
| `estimated_start_time` | `DATETIME` | `NULL` | Thời điểm bắt đầu dự kiến do điều phối viên xác định |
| `estimated_end_time` | `DATETIME` | `NULL` | Thời điểm kết thúc dự kiến do điều phối viên xác định |
| `status` | `VARCHAR(20)` | `NOT NULL, DEFAULT 'UNASSIGNED'` | Trạng thái máy trạng thái của chuyến hàng |
| `assigned_truck_id` | `INTEGER` | `NULL, FOREIGN KEY (trucks.id)` | Khóa ngoại liên kết tới xe tải được phân công |
| `assigned_driver_id` | `INTEGER` | `NULL, FOREIGN KEY (drivers.id)` | Khóa ngoại liên kết tới tài xế được phân công |
| `notes` | `VARCHAR(500)` | `NULL` | Ghi chú điều phối hoặc yêu cầu đặc biệt của khách hàng |
| `created_at` | `DATETIME` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Thời điểm tạo chuyến hàng |
| `updated_at` | `DATETIME` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Thời điểm cập nhật cuối cùng |

---

### 1.2. Bảng `resource_bookings` (Lịch Chiếm Dụng Nguồn Lực)

Lưu trữ các khoảng thời gian xe tải hoặc tài xế bị chiếm dụng bởi chuyến hàng hoặc hợp đồng cho thuê xe, phục vụ kiểm soát xung đột trùng lịch (BR-07, BR-08).

| Tên trường | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Khóa chính định danh lịch chiếm dụng |
| `resource_type` | `VARCHAR(20)` | `NOT NULL` | Loại nguồn lực: `TRUCK` hoặc `DRIVER` |
| `resource_id` | `INTEGER` | `NOT NULL, INDEX` | Khóa ngoại mềm trỏ tới `trucks.id` hoặc `drivers.id` |
| `reference_code` | `VARCHAR(50)` | `NOT NULL, INDEX` | Mã đơn hoặc mã hợp đồng chiếm dụng (ví dụ: `TRIP-2026-001`) |
| `service_type` | `VARCHAR(20)` | `NOT NULL, DEFAULT 'FREIGHT'` | Loại dịch vụ: `FREIGHT` (Vận tải), `RENTAL` (Cho thuê) |
| `start_time` | `DATETIME` | `NOT NULL` | Thời điểm bắt đầu chiếm dụng nguồn lực |
| `end_time` | `DATETIME` | `NOT NULL` | Thời điểm kết thúc chiếm dụng nguồn lực |
| `status` | `VARCHAR(20)` | `NOT NULL, DEFAULT 'CONFIRMED'` | Trạng thái booking: `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` |
| `created_at` | `DATETIME` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Thời điểm tạo booking |
| `updated_at` | `DATETIME` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Thời điểm cập nhật cuối cùng |

---

## 2. Enums & Ràng buộc Kiểm tra (Check Constraints)

### 2.1. Enum Trạng thái Chuyến hàng (`TripStatus`)
```python
class TripStatus(str, enum.Enum):
    UNASSIGNED = "UNASSIGNED"  # Đơn hàng mới tạo, chưa có xe/tài xế
    ASSIGNED = "ASSIGNED"      # Đã điều phối xe và tài xế thành công
    PICKED_UP = "PICKED_UP"    # Đã nhận hàng tại điểm lấy hàng
    IN_TRANSIT = "IN_TRANSIT"  # Đang trên đường vận chuyển
    DELIVERED = "DELIVERED"    # Đã giao hàng tới điểm nhận
    COMPLETED = "COMPLETED"    # Đã xác nhận hoàn tất chuyến hàng
    CANCELLED = "CANCELLED"    # Đã hủy đơn hàng
```

### 2.2. Enum Loại Dịch vụ (`ServiceType`)
```python
class ServiceType(str, enum.Enum):
    FREIGHT = "FREIGHT"  # Vận chuyển hàng hóa đường bộ
    RENTAL = "RENTAL"    # Cho thuê xe (tự lái hoặc kèm tài xế)
```

### 2.3. Check Constraints
- `ck_trip_status_valid`: `CHECK (status IN ('UNASSIGNED', 'ASSIGNED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED', 'COMPLETED', 'CANCELLED'))`
- `ck_trip_cargo_weight_positive`: `CHECK (cargo_weight_kg > 0)`
- `ck_booking_service_type_valid`: `CHECK (service_type IN ('FREIGHT', 'RENTAL'))`
- `ck_booking_resource_type_valid`: `CHECK (resource_type IN ('TRUCK', 'DRIVER'))`
- `ck_booking_status_valid`: `CHECK (status IN ('CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'))`

---

## 3. Máy Trạng thái (State Machine Transitions)

```
                 +-------------------+
                 |    UNASSIGNED     | <------+ (Gỡ phân công / Unassign)
                 +-------------------+        |
                           |                  |
              [Phân công hợp lệ - TRN-02]     |
                           v                  |
                 +-------------------+        |
                 |     ASSIGNED      | +------+
                 +-------------------+
                           |
             [Đổi xe/tài xế hợp lệ - TRN-02]
              (Giải phóng booking cũ, tạo mới)
                           |
                           v
            [Xác nhận nhận hàng - TRN-03]
                           |
                           v
                 +-------------------+
                 |     PICKED_UP     | (Từ mốc này trở đi KHÓA ĐỔI PHÂN CÔNG!)
                 +-------------------+
```

### Quy tắc chuyển đổi trạng thái:
1. **Khởi tạo (`UNASSIGNED`)**: `assigned_truck_id = None`, `assigned_driver_id = None`. Không có booking nào tồn tại.
2. **Phân công (`UNASSIGNED` ➔ `ASSIGNED`)**:
   - Điều kiện tiên quyết: Chuyến đang ở trạng thái `UNASSIGNED`.
   - Kiểm tra: `truck.capacity_kg >= trip.cargo_weight_kg`.
   - Kiểm tra: `truck.status == 'ACTIVE'`, `driver.status == 'ACTIVE'`.
   - Kiểm tra: Không trùng lịch trong `[start_time, end_time]` cho cả xe và tài xế.
   - Thao tác: Cập nhật `assigned_truck_id`, `assigned_driver_id`, `estimated_start_time`, `estimated_end_time`, `status = 'ASSIGNED'`. Tạo 2 bản ghi `ResourceBooking` (`status = 'CONFIRMED'`).
3. **Đổi phân công (`ASSIGNED` ➔ `ASSIGNED`)**:
   - Điều kiện tiên quyết: Chuyến đang ở trạng thái `ASSIGNED`.
   - Thao tác: Kiểm tra nguồn lực mới, nếu hợp lệ: giải phóng booking cũ (`CANCELLED`), tạo booking mới, cập nhật chuyến. Nếu không hợp lệ: rollback giữ nguyên phân công cũ.
4. **Hủy phân công (`ASSIGNED` ➔ `UNASSIGNED`)**:
   - Điều kiện tiên quyết: Chuyến đang ở trạng thái `ASSIGNED`.
   - Thao tác: Hủy toàn bộ booking của chuyến (`CANCELLED`), xóa gán nguồn lực, đưa chuyến về `UNASSIGNED`.
5. **Khóa can thiệp (`PICKED_UP`, `IN_TRANSIT`, `DELIVERED`, `COMPLETED`)**:
   - Tuyệt đối cấm gọi thao tác phân công, đổi hoặc hủy phân công.
