# Phase 0: Technical Research & Architectural Decisions

**Feature**: TRN-05 Quản lý sự cố và chậm tiến độ (Incident & Delay Management)  
**Spec**: [spec.md](spec.md)  
**Date**: 2026-11-25

---

## 1. Nghiên Cứu 1: Mở Rộng Mô Hình Dữ Liệu Sự Cố (`TripIssue`) & Chu Trình Trạng Thái

### Bối cảnh & Yêu cầu
Trong phân hệ TRN-04, model `TripIssue` đã được khởi tạo cơ bản để phục vụ việc ghi nhận tự động khi giao hàng thất bại (`DELIVERY_FAILED`). Trong TRN-05, tài liệu `03_Freight_Transportation.pdf` yêu cầu:
- Ghi nhận đầy đủ: Loại sự cố (`issue_type`), thời điểm phát sinh (`occurred_at`), mô tả chi tiết (`description`), người phụ trách xử lý (`handled_by`), thời điểm dự kiến khắc phục (`estimated_resolution_time`), và trạng thái `OPEN` / `RESOLVED`.
- Đóng sự cố bắt buộc ghi nhận kết quả xử lý (`resolution_notes`) và thời điểm hoàn tất (`resolved_at`).

### Quyết định kỹ thuật
- **Mở rộng Model `TripIssue`**:
  - `occurred_at` (DATETIME, NOT NULL, DEFAULT UTC NOW): Thời điểm thực tế xảy ra sự cố.
  - `handled_by` (VARCHAR(150), NULLABLE): Họ tên / đơn vị / số điện thoại người phụ trách xử lý sự cố.
  - `estimated_resolution_time` (DATETIME, NULLABLE): Dự kiến thời điểm hoàn thành khắc phục.
  - `resolution_notes` (VARCHAR(1000), NULLABLE): Kết quả xử lý khi đóng sự cố.
  - `resolved_at` (DATETIME, NULLABLE): Thời điểm đánh dấu hoàn tất xử lý.
- **Phân loại sự cố chuẩn hóa (Standardized Issue Categories)**:
  - `VEHICLE_BREAKDOWN`: Hỏng hóc phương tiện (thủng lốp, chết máy, đứt xích...).
  - `TRAFFIC_CONGESTION`: Kẹt xe / Ùn tắc giao thông nghiêm trọng.
  - `ACCIDENT`: Va chạm / Tai nạn giao thông.
  - `CARGO_DAMAGE`: Hư hại / Bể vỡ / Móp méo bao bì hàng hóa.
  - `WEATHER_DELAY`: Bão lũ, sạt lở đèo, thời tiết bất lợi.
  - `DELIVERY_FAILED`: Giao hàng thất bại (từ TRN-04).
  - `OTHER`: Sự cố phát sinh khác.
- **State Machine của Sự cố**:
  - `OPEN` ➔ `RESOLVED` (kèm ghi chú kết quả giải quyết).
  - `OPEN` ➔ `CANCELLED` (trường hợp biên bản lập nhầm lẫn).

### Đánh giá phương án thay thế
- *Phương án thay thế*: Sử dụng bảng tự do không cấu trúc (Key-Value hoặc trường JSON).
- *Lý do loại bỏ*: Khó kiểm soát validation, không đảm bảo tính toàn vẹn khi truy vấn báo cáo và khó ràng buộc tính bắt buộc của `resolution_notes` khi đóng sự cố.

---

## 2. Nghiên Cứu 2: Cơ Chế Phát Hiện & Tính Toán Cờ Quá Hạn Vận Hành (`DELAYED` / `OVERDUE`)

### Bối cảnh & Yêu cầu
Tài liệu quy định: "Cờ quá hạn vận hành xuất hiện khi thời gian hiện tại vượt kết thúc cam kết (`estimated_end_time`) mà chuyến chưa `DELIVERED`, `COMPLETED`, hoặc `CANCELLED`." Hệ thống tuyệt đối không tự suy diễn vị trí GPS hay tự đổi trạng thái giao.

### Quyết định kỹ thuật
- **Dynamic Property / Query-Level Evaluation**:
  - Không sử dụng tiến độ chạy nền (background cron job / daemon) để cập nhật cờ tĩnh vào DB nhằm tránh trễ nhịp và tăng độ phức tạp vận hành.
  - Thuộc tính `is_delayed` được tính toán thời gian thực (`@property` trên Model `Trip` và biểu thức truy vấn SQL tại `TripRepository`):
    ```python
    @property
    def is_delayed(self) -> bool:
        if self.status in [TripStatus.DELIVERED.value, TripStatus.COMPLETED.value, TripStatus.CANCELLED.value]:
            return False
        if not self.estimated_end_time:
            return False
        return datetime.now() > self.estimated_end_time
    ```
  - Trong `TripRepository`: Xây dựng bộ lọc SQL `filter_delayed_trips` sử dụng biểu thức:
    `Trip.status.notin_(['DELIVERED', 'COMPLETED', 'CANCELLED']) & (Trip.estimated_end_time < datetime.now())`.
  - Hiển thị trên giao diện: Badge màu đỏ `badge bg-danger` với icon `bi bi-alarm-fill` và tính toán số giờ trễ (e.g. "Trễ 2h 15m").

### Đánh giá phương án thay thế
- *Phương án thay thế*: Dùng Celery / APScheduler quét định kỳ mỗi 5 phút để cập nhật cột `is_delayed = 1` vào DB.
- *Lý do loại bỏ*: Vi phạm nguyên tắc Simplicity của Hiến pháp dự án. Tốn tài nguyên, có độ trễ giữa các lần quét, và dễ gây sai lệch trạng thái nếu worker bị gián đoạn.

---

## 3. Nghiên Cứu 3: Điều Chỉnh Lùi Lịch Dự Kiến & Kiểm Soát Xung Đột Lịch Tương Lai

### Bối cảnh & Yêu cầu
Khi chuyến hàng bị chậm do sự cố, điều phối viên cần cập nhật lùi `estimated_end_time`. Tài liệu quy định:
"Khi cập nhật thời gian kết thúc dự kiến, kiểm tra lại lịch; nếu chồng lịch tiếp theo, giữ lịch đang có và hiển thị các booking xung đột để điều phối đổi/dời booking tương lai. Việc xe đang sử dụng vẫn chặn bắt đầu công việc sau theo BR-09."

### Quyết định kỹ thuật
- **Luồng xử lý Reschedule**:
  1. Tiếp nhận `new_estimated_end_time` từ DSP. Kiểm tra `new_estimated_end_time > trip.estimated_start_time`.
  2. Lấy danh sách booking hiện tại của chuyến hàng trong `resource_bookings` (gồm 1 booking xe tải và 1 booking tài xế).
  3. Quét kiểm tra xung đột với các booking tương lai trong khoảng mở rộng `(old_estimated_end_time, new_estimated_end_time]`:
     ```sql
     SELECT rb FROM resource_bookings rb
     WHERE rb.trip_id != :current_trip_id
       AND rb.status IN ('BOOKED', 'IN_PROGRESS')
       AND (rb.resource_id = :truck_id AND rb.resource_type = 'TRUCK'
            OR rb.resource_id = :driver_id AND rb.resource_type = 'DRIVER')
       AND rb.start_time < :new_estimated_end_time
       AND rb.end_time > :old_estimated_end_time
     ```
  4. Nếu có xung đột:
     - **Vẫn cho phép cập nhật**: Cập nhật `estimated_end_time` của chuyến hàng hiện tại và cập nhật `end_time = new_estimated_end_time` cho các booking của chuyến hiện tại (đảm bảo phản ánh đúng thực tế chiếm dụng).
     - **Thu thập danh sách xung đột**: Trả về danh sách chi tiết các booking tương lai bị ảnh hưởng (Mã chuyến tham chiếu, loại dịch vụ `FREIGHT` / `RENTAL`, tên tài nguyên bị trùng, khoảng thời gian bị chồng lấn).
     - **Hiển thị Modal cảnh báo xung đột (HTTP 409 Conflict Response)**: Báo cho DSP biết các chuyến tương lai cần dời lịch hoặc gỡ xe/tài xế để gán nguồn lực khác.
  5. Tiếp tục áp dụng **BR-09**: Nếu xe/tài xế chưa hoàn tất chuyến hiện tại (`IN_PROGRESS`), ở chuyến kế tiếp dù đến giờ bắt đầu cũng không thể bấm `PICKED_UP`.
  6. Ghi nhận sự kiện `SCHEDULE_DELAYED` vào bảng `trip_events`.

### Đánh giá phương án thay thế
- *Phương án thay thế*: Chặn tuyệt đối không cho phép gia hạn lịch nếu có booking tương lai.
- *Lý do loại bỏ*: Trái ngược với tài liệu nghiệp vụ ("giữ lịch đang có và hiển thị các booking xung đột để điều phối đổi/dời booking tương lai"). Ngoài đời thực, xe đang kẹt trên cao tốc thì không thể bắt xe kết thúc đúng hạn; việc phải làm là ghi nhận thực tế xe bị trễ và cảnh báo điều phối viên đi tìm xe khác cho đơn sau.

---

## 4. Nghiên Cứu 4: Tính Độc Lập Giữa Sự Cố, Doanh Thu (SAL-08) và Máy Trạng Thái

### Bối cảnh & Yêu cầu
Tài liệu quy định:
- "Sự cố không tự làm chuyến hoàn thành hoặc tự đổi giá; phụ phí theo SAL-08."
- "Hệ thống không tự suy diễn vị trí GPS hoặc trạng thái giao từ thời gian dự kiến; trạng thái chỉ đổi theo sự kiện nghiệp vụ đã được ghi nhận."

### Quyết định kỹ thuật
- **Không tự động chuyển trạng thái**: Sự cố được ghi nhận độc lập qua bảng `trip_issues`. Chuyến hàng vẫn giữ nguyên trạng thái vận hành hiện tại (`ASSIGNED`, `PICKED_UP`, hoặc `IN_TRANSIT`).
- **Không tự động cộng tiền / thay đổi giá cước**: Cước phí đơn hàng giữ nguyên. Các chi phí phát sinh (như phí neo xe, bốc xếp, cứu hộ) sẽ do bộ phận Kinh doanh ghi nhận biên bản phụ phí ngoài phạm vi của TRN-05 theo quy trình SAL-08.
- **Chặn hoàn tất nếu còn sự cố OPEN liên quan đến giao hàng**: Nếu chuyến hàng có sự cố loại `DELIVERY_FAILED` chưa được giải quyết, chuyến hàng không thể hoàn tất.

---

## 5. Nghiên Cứu 5: Phân Quyền Vai Trò (RBAC) & Trải Nghiệm Giao Diện Người Dùng

### Bối cảnh & Yêu cầu
- Vai trò `DSP` (Điều phối viên): Toàn quyền ghi nhận sự cố, cập nhật tiến độ, đóng sự cố, điều chỉnh lùi lịch.
- Vai trò `SAL` (Kinh doanh) và `MGR` (Quản lý): Chỉ xem danh mục sự cố, theo dõi cờ quá hạn để giải thích với khách hàng (Read-only, HTTP 403 Forbidden khi thao tác ghi).

### Quyết định kỹ thuật
- FastAPI Dependencies: Sử dụng `require_role(["DSP"])` cho tất cả các endpoint ghi (`POST /trips/{id}/issues`, `POST /trips/{id}/issues/{issue_id}/resolve`, `POST /trips/{id}/reschedule`).
- Giao diện Jinja2:
  - Nút "Báo Cáo Sự Cố", "Giải Quyết Sự Cố", "Gia Hạn Lịch" được bọc trong điều kiện:
    `{% if current_user and current_user.role == 'DSP' %}`.
  - Tab lọc tại danh mục chuyến hàng: Bổ sung 2 tab:
    - "Có Sự Cố": Lọc các chuyến hàng có sự cố `OPEN`.
    - "Quá Hạn Vận Hành": Lọc các chuyến hàng có `is_delayed == True`.
  - Thiết kế bảng cảnh báo xung đột (Conflict Warning Modal) theo phong cách Bootstrap 5 của `frontend/DESIGN.md`.

---

## 6. Kết Luận Kiến Trúc (Architecture Summary)

Tất cả các quyết định trên tuân thủ nghiêm ngặt 5 nguyên tắc Hiến pháp dự án:
1. **Layered Architecture**: Router ➔ `IncidentService` / `TripTrackingService` ➔ `TripIssueRepository` / `ResourceBookingRepository` ➔ Database.
2. **State Machine Integrity**: Trạng thái chuyến hàng không bị nhảy cóc hay can thiệp tự động; bảo toàn lịch sử bằng chứng từ và sự kiện.
3. **Strict Concurrency & ACID**: Giao dịch cập nhật lịch trình được bảo vệ trong Transaction an toàn.
4. **Test-Driven Verification**: Viết unit test và integration test bao phủ đầy đủ kịch bản trễ hạn, xung đột lịch tương lai và phân quyền.
5. **Observability & Security**: Dùng Python standard `logging`, kiểm soát cookie session, không log thông tin nhạy cảm.
