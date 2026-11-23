# Research & Technical Decisions: TRN-01 Quản lý xe và tài xế

**Feature**: `001-truck-and-driver-management`  
**Date**: 2026-11-23  
**Status**: Completed  

---

## 1. Chuẩn hóa biển số xe (License Plate Normalization)

### Vấn đề cần giải quyết
Biển số xe tại Việt Nam có nhiều dạng nhập liệu khác nhau từ người dùng: `29C-123.45`, `29C12345`, `29c 123.45`, `29-C1-123.45`. Nếu lưu trực tiếp chuỗi thô vào CSDL sẽ dẫn đến việc tạo trùng xe hoặc tìm kiếm không chính xác.

### Quyết định kỹ thuật
- **Thuật toán chuẩn hóa**:
  1. Loại bỏ toàn bộ khoảng trắng, dấu gạch ngang (`-`), dấu chấm (`.`): `re.sub(r'[^A-Za-z0-9]', '', raw_plate)`.
  2. Viết hoa toàn bộ (`.upper()`).
  3. Kiểm tra Regex hợp lệ biển số Việt Nam cơ bản: `^[0-9]{2}[A-Z]{1,2}[0-9]{4,6}$`.
- **Lưu trữ CSDL**:
  - `plate_number`: Biển số hiển thị gốc (ví dụ: `29C-123.45`).
  - `normalized_plate`: Biển số đã chuẩn hóa (ví dụ: `29C12345`), có ràng buộc `UNIQUE` và chỉ mục `INDEX` trong database.
- **Lý do chọn**: Đảm bảo toàn vẹn dữ liệu ở cấp CSDL, ngăn ngừa 100% trường hợp trùng biển số do sai khác format nhập liệu.
- **Giải pháp thay thế bị bác bỏ**:
  - *Chỉ lưu biển số đã chuẩn hóa, không lưu biển số hiển thị*: Bị từ chối vì người dùng muốn xem biển số đúng định dạng đăng kiểm có dấu gạch/chấm.
  - *Chỉ kiểm tra trùng bằng LIKE / Regex trong query*: Bị từ chối vì làm giảm hiệu năng truy vấn và không thể tận dụng Unique Constraint của DB.

---

## 2. Kiểm tra tính khả dụng & Lịch trình động (Dynamic Availability & Conflict Check)

### Vấn đề cần giải quyết
FR-006 & FR-009: Lịch rảnh/bận của xe và tài xế không được lưu cứng dưới dạng cờ tĩnh (`is_busy = True/False`) mà phải được tính toán tự động dựa trên các lịch booking và chuyến xe thực tế. Ngoài ra, khi chuyển xe/tài xế sang `MAINTENANCE` hoặc `INACTIVE`, hệ thống phải kiểm tra xem có lịch phân công trong tương lai hay không.

### Quyết định kỹ thuật
- **Trạng thái thực thể (Lifecycle Status)**:
  - `TruckStatus`: `ACTIVE`, `MAINTENANCE`, `INACTIVE`
  - `DriverStatus`: `ACTIVE`, `INACTIVE`
- **Mô hình tính toán rảnh/bận động (Dynamic Query)**:
  - Một nguồn lực (Xe / Tài xế) được coi là **SẴN SÀNG (AVAILABLE)** tại thời điểm hoặc khoảng thời gian `[T_start, T_end]` khi và chỉ khi:
    1. Trạng thái cơ bản là `ACTIVE`.
    2. KHÔNG tồn tại bất kỳ bản ghi `ResourceBooking` nào ở trạng thái `CONFIRMED` hoặc `IN_PROGRESS` thỏa mãn điều kiện giao nhau về thời gian:
       `booking.start_time < T_end AND booking.end_time > T_start`.
- **Ràng buộc khi đổi trạng thái sang không sẵn sàng (`MAINTENANCE` / `INACTIVE`)**:
  - Service Layer thực hiện truy vấn kiểm tra:
    ```sql
    SELECT COUNT(*) FROM resource_bookings 
    WHERE resource_type = :type AND resource_id = :id
      AND status IN ('CONFIRMED', 'IN_PROGRESS')
      AND end_time >= CURRENT_TIMESTAMP;
    ```
  - Nếu `COUNT > 0`: Ném `BusinessRuleViolationError`, trả về danh sách chi tiết các `booking_id`, `start_time`, `end_time` bị xung đột và CHẶN cập nhật trạng thái.
- **Lý do chọn**: Triệt tiêu hoàn toàn hiện tượng dữ liệu không nhất quán (*Stale state*) thường xảy ra nếu dùng cờ tĩnh.

---

## 3. Khóa xóa cứng (Soft Delete & Immutable Audit Trail)

### Vấn đề cần giải quyết
Hiến pháp dự án (Nguyên tắc II) và FR-005 yêu cầu cấm xóa cứng bất kỳ xe hoặc tài xế nào đã có lịch sử tham gia giao dịch hoặc cuốc vận tải.

### Quyết định kỹ thuật
- Phương thức `delete_truck(truck_id)` và `delete_driver(driver_id)` trong Service Layer:
  1. Kiểm tra xem nguồn lực có tồn tại bất kỳ bản ghi nào trong bảng `ResourceBooking` (hoặc `Trip` sau này) hay không:
     ```python
     has_history = booking_repo.has_booking_history(resource_type, resource_id)
     ```
  2. Nếu `has_history == True`: Chặn xóa cứng, ném `BusinessRuleViolationError("Không thể xóa nguồn lực đã có lịch sử hoạt động. Vui lòng chuyển trạng thái sang INACTIVE.")`.
  3. Nếu `has_history == False` (ví dụ: bản ghi vừa tạo nhầm trong test): Cho phép xóa hoặc chuyển sang `INACTIVE` theo chính sách.
- Trong CSDL, không thiết lập `ON DELETE CASCADE` tới bảng `Truck` hay `Driver` để đảm bảo bảo vệ tầng DB (Foreign Key Constraint Violation nếu cố tình xóa qua raw DB).

---

## 4. Chuẩn hóa API Response & Xử lý lỗi tập trung

### Vấn đề cần giải quyết
Tuân thủ tuyệt đối quy định trong `AGENTS.md`:
- API JSON format: `{"success": bool, "data": Any, "error": str | None, "meta": dict}`.
- Không để lộ Exception thô (stack trace) ra client.
- Dùng logging SLF4J / Python standard `logging`, tuyệt đối không dùng `print()`.

### Quyết định kỹ thuật
- **Pydantic Response Envelope**:
  ```python
  class ApiResponse(BaseModel, Generic[T]):
      success: bool = True
      data: Optional[T] = None
      error: Optional[str] = None
      meta: Optional[Dict[str, Any]] = Field(default_factory=dict)
  ```
- **Centralized Exception Handler**:
  - Đăng ký exception handler cho `DomainException` (EntityNotFoundError -> 404, BusinessRuleViolationError -> 400, ConflictError -> 409).
  - Đăng ký exception handler toàn cục cho `Exception` chưa lường trước:
    - Ghi log: `logger.error("Internal server error occurred", exc_info=True)`.
    - Trả về JSON: `{"success": False, "data": None, "error": "Có lỗi xảy ra, vui lòng thử lại sau.", "meta": {}}` với HTTP 500.

---

## 5. Kiến trúc phân tầng (Clean Layered Architecture)

### Cấu trúc mô-đun
```text
Browser / Client (Jinja2 / API)
        │
        ▼
FastAPI Routers (src/api/v1/trucks.py, src/api/v1/drivers.py, src/web/...)
  - Validate HTTP request / Pydantic Schemas
  - Map URLs (/admin/trucks, /admin/drivers, /api/v1/trucks, /api/v1/drivers)
        │
        ▼
Service Layer (src/services/truck_service.py, src/services/driver_service.py)
  - Business logic: chuẩn hóa biển số, validate tải trọng > 0, kiểm tra xung đột lịch tương lai
  - Orchestration & Transaction boundary
        │
        ▼
Repository Layer (src/repositories/truck_repo.py, src/repositories/driver_repo.py)
  - Data access thông qua SQLAlchemy Session
  - Parameterized queries / ORM methods
        │
        ▼
Database Models (src/models/truck.py, src/models/driver.py, src/models/booking.py)
```

Tất cả các quyết định trên đều tuân thủ 100% Hiến pháp dự án (`constitution.md`) và chỉ thị của `AGENTS.md`.
