# Research & Architecture Decisions: TRN-04 Xác nhận giao hàng và hoàn tất

**Branch**: `005-delivery-and-completion` | **Date**: 2026-11-25 | **Feature**: [spec.md](spec.md)

Tài liệu này ghi nhận kết quả nghiên cứu kỹ thuật, phân tích phương án và các quyết định kiến trúc phục vụ triển khai module **TRN-04: Xác nhận giao hàng và hoàn tất**.

---

## 1. Cơ chế Quản lý & Lưu trữ Tệp Bằng chứng Bàn giao (POD Evidence)

### Bối cảnh & Yêu cầu
Theo tài liệu nghiệp vụ gốc `03_Freight_Transportation.pdf` và tiêu chuẩn phi chức năng NFR-07:
- Để xác nhận giao hàng (`DELIVERED`), hệ thống bắt buộc phải có ít nhất một tệp bằng chứng bàn giao (Proof of Delivery - POD).
- Định dạng tệp hợp lệ: PDF, JPG, JPEG, PNG; dung lượng mỗi tệp $\le 10$ MB.
- Tệp cần được lưu an toàn, hỗ trợ xem trước (preview) và tải về đối soát cước.

### Quyết định kỹ thuật
- **Lưu trữ tệp:** Lưu trữ trên hệ thống tệp cục bộ (Local Filesystem) tại thư mục `src/static/uploads/evidence/`.
- **Đặt tên tệp an toàn (Safe File Naming):** Sử dụng chuỗi định danh duy nhất UUID kết hợp với tên tệp gốc đã được làm sạch ký tự lạ (`<uuid4>_<sanitized_filename>`) nhằm:
  1. Chống ghi đè khi nhiều tài xế/điều phối tải lên tệp có tên giống nhau (ví dụ: `bien_ban.pdf`, `photo.jpg`).
  2. Ngăn chặn triệt để lỗ hổng Path Traversal (`../`).
- **Lưu trữ Metadata trong Database:** Tạo bảng mới `trip_evidence` chứa:
  - `id`: Khóa chính tự tăng
  - `trip_id`: Khóa ngoại liên kết với bảng `trips` (CASCADE ON DELETE)
  - `file_path`: Đường dẫn tương đối lưu tệp (ví dụ: `uploads/evidence/123e4567_pod.jpg`)
  - `file_name`: Tên gốc do người dùng tải lên
  - `file_size_bytes`: Kích thước tệp tính bằng bytes
  - `mime_type`: Loại MIME (ví dụ: `application/pdf`, `image/jpeg`, `image/png`)
  - `evidence_type`: Phân loại chứng từ (mặc định: `POD`, hoặc `WEIGHING_SLIP`, `INCIDENT_PHOTO`)
  - `uploaded_by_user_id`: Định danh người dùng thực hiện tải lên
  - `created_at`: Thời điểm tải lên (UTC)

### Các phương án đã so sánh
| Phương án | Ưu điểm | Nhược điểm | Đánh giá |
|-----------|---------|------------|----------|
| **Lưu trữ File System cục bộ + Metadata trong DB** *(Được chọn)* | Hiệu năng cao, cấu hình đơn giản, database nhẹ, dễ sao lưu, tuân thủ nguyên tắc Simplicity. | Cần quản lý quyền truy cập thư mục máy chủ. | **CHỌN** |
| **Lưu BLOB trực tiếp trong Database** | Dữ liệu gom chung một chỗ trong file `.db`. | Database phình to nhanh chóng, làm chậm truy vấn SQL và sao lưu hệ thống. | **LOẠI** |
| **Lưu trên Cloud Object Storage (AWS S3 / GCP GCS)** | Mở rộng không giới hạn, phân tán tốt. | Phức tạp hóa hạ tầng cho môi trường on-premise/local dev, phát sinh chi phí và secret key ngoài. | **LOẠI** (Có thể cấu hình adapter mở rộng sau nếu cần) |

---

## 2. Kiểm Soát Máy Trạng Thái (State Machine) & Quy Tắc Thời Gian

### Bối cảnh & Yêu cầu
Vòng đời vận chuyển tuân thủ máy trạng thái bất biến quy định tại Hiến pháp dự án:
$$\text{UNASSIGNED} \longrightarrow \text{ASSIGNED} \longrightarrow \text{PICKED\_UP} \longrightarrow \text{IN\_TRANSIT} \longrightarrow \text{DELIVERED} \longrightarrow \text{COMPLETED}$$
Tuyệt đối không nhảy cóc trạng thái. Mọi bước chuyển đổi phải xác thực mốc thời gian logic và lưu vết bất biến.

### Quyết định kỹ thuật

#### Chặng 1: Xác nhận Giao hàng (`IN_TRANSIT` ➔ `DELIVERED`)
- **Điều kiện tiền đề:** `trip.status == TripStatus.IN_TRANSIT.value`.
- **Ràng buộc thời gian:** `actual_delivery_time >= trip.actual_pickup_time`.
- **Ràng buộc chứng từ:** Tối thiểu 1 tệp POD hợp lệ (PDF/JPG/PNG).
- **Hành động nghiệp vụ trong 1 Transaction:**
  1. Cập nhật `trip.status = TripStatus.DELIVERED.value`.
  2. Cập nhật `trip.actual_delivery_time`, `trip.recipient_name`, `trip.delivery_notes`, `trip.delivery_recorded_at = UTC NOW`.
  3. Lưu các bản ghi `TripEvidence`.
  4. Ghi sự kiện `TripEvent`: `event_type = 'DELIVERY_CONFIRMED'`, `from_status = 'IN_TRANSIT'`, `to_status = 'DELIVERED'`, `actual_time = actual_delivery_time`.

#### Chặng 2: Giao hàng thất bại (`FAILED`)
- **Điều kiện tiền đề:** `trip.status == TripStatus.IN_TRANSIT.value`.
- **Quy tắc nghiệp vụ:** Giữ nguyên `trip.status = IN_TRANSIT`, không chuyển sang `DELIVERED`.
- **Hành động nghiệp vụ:**
  1. Tạo bản ghi sự cố `TripIssue`: `issue_type = 'DELIVERY_FAILED'`, `description = notes`, `status = 'OPEN'`, `reported_by = user_id`.
  2. Nếu có tệp đính kèm (ảnh biên bản sự cố/ảnh hàng hỏng), lưu vào `TripEvidence` với `evidence_type = 'INCIDENT_PHOTO'`.
  3. Ghi sự kiện `TripEvent`: `event_type = 'DELIVERY_FAILED'`, `from_status = 'IN_TRANSIT'`, `to_status = 'IN_TRANSIT'`.

#### Chặng 3: Chốt Hoàn tất Chuyến hàng (`DELIVERED` ➔ `COMPLETED`)
- **Điều kiện tiền đề:**
  - `trip.status == TripStatus.DELIVERED.value`.
  - Đã có ít nhất 1 tệp `TripEvidence` gắn với chuyến.
  - Không có khoản phụ phí nào đang ở trạng thái chờ duyệt (`PENDING`).
- **Ràng buộc thời gian:**
  - `actual_completed_time >= trip.actual_delivery_time`.
  - `actual_completed_time <= current_time` (Không được ở tương lai).
- **Hành động nghiệp vụ trong 1 Transaction:**
  1. Cập nhật `trip.status = TripStatus.COMPLETED.value`.
  2. Cập nhật `trip.actual_completed_time`, `trip.completed_recorded_at = UTC NOW`.
  3. Cập nhật các bản ghi `ResourceBooking` của chuyến (cho cả Xe tải và Tài xế):
     - `status = BookingStatus.COMPLETED.value`.
     - `end_time = actual_completed_time`.
  4. Ghi sự kiện `TripEvent`: `event_type = 'TRIP_COMPLETED'`, `from_status = 'DELIVERED'`, `to_status = 'COMPLETED'`, `actual_time = actual_completed_time`.

---

## 3. Cơ Chế Giải Phóng Nguồn Lực và Đồng Bộ Quy Tắc BR-09

### Phân tích logic giải phóng
Quy tắc BR-09 quy định: *Không cho phép xe tải hoặc tài xế nhận hàng (`PICKED_UP`) cho chuyến mới nếu họ đang dở dang một chuyến hàng khác có booking ở trạng thái `IN_PROGRESS`.*

Phương thức kiểm tra hiện tại trong `ResourceBookingRepository`:
```python
def has_in_progress_booking(self, resource_type: str, resource_id: int, exclude_reference_code: Optional[str] = None) -> bool:
    return self.db.query(ResourceBooking).filter(
        ResourceBooking.resource_type == resource_type,
        ResourceBooking.resource_id == resource_id,
        ResourceBooking.status == BookingStatus.IN_PROGRESS.value,
    ).count() > 0
```

### Quyết định thiết kế
1. Khi chuyến hàng đạt mốc `COMPLETED`, toàn bộ `ResourceBooking` liên quan được chuyển từ `IN_PROGRESS` sang `COMPLETED`.
2. Khi `status == COMPLETED`, hàm `has_in_progress_booking` sẽ lập tức trả về `False`.
3. Nhờ đó, Xe tải và Tài xế được tự động giải phóng hoàn toàn và có thể ngay lập tức thực hiện nhận hàng cho chuyến tiếp theo mà không bị chặn bởi BR-09.

---

## 4. Kiểm Soát Phụ Phí (Surcharges) Khi Đóng Chuyến

### Bối cảnh từ SRS & PDF
Tài liệu quy định: *"Khi DELIVERED, được chốt COMPLETED sau khi đủ bằng chứng và không còn phụ phí PENDING. Hoàn tất cập nhật đơn COMPLETED và giải phóng nguồn lực; không phụ thuộc đã thu đủ tiền chặn bắt đầu công việc sau theo BR-09."*

### Quyết định thiết kế
- Hệ thống hỗ trợ kiểm tra phụ phí phát sinh (nếu có bảng phụ phí hoặc cờ trạng thái trên sự cố).
- Trong phạm vi module TRN-04, `DeliveryService.complete_trip` kiểm tra: nếu có bất kỳ khoản phụ phí nào gắn với chuyến hàng đang ở trạng thái `PENDING`, hệ thống ném ngoại lệ `BusinessRuleViolationError` yêu cầu xử lý duyệt/hủy phụ phí trước khi đóng chuyến.
- Nếu không có phụ phí `PENDING`, cho phép đóng chuyến ngay lập tức.

---

## 5. An Toàn Tải Tệp & Bảo Vệ Tải Về (File Serving Security)

### Quyết định thiết kế
1. **Endpoint Tải về / Xem trước:**
   - Web SSR: `GET /trips/{id}/evidence/{evidence_id}/download`
   - REST API: `GET /api/v1/trips/{id}/evidence/{evidence_id}/download`
2. **Kiểm tra xác thực:** Chỉ người dùng đã đăng nhập (`UserSession` hợp lệ) mới được tải/xem tệp.
3. **Phản hồi HTTP:** Trả về `FileResponse` với `media_type` tương ứng của tệp (`application/pdf`, `image/png`, `image/jpeg`). Đối với ảnh và PDF, trình duyệt có thể render trực tiếp trên tab mới hoặc tải về máy.
4. **Kiểm tra tồn tại vật lý:** Nếu bản ghi có trong cơ sở dữ liệu nhưng tệp vật lý bị mất trên đĩa, trả về mã lỗi 404 thân thiện thay vì làm sập ứng dụng.
