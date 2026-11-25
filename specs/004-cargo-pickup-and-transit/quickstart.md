# Quickstart & Validation Guide: TRN-03 Ghi nhận nhận hàng và vận chuyển

Tài liệu hướng dẫn kiểm thử tự động (`pytest`) và thực thi các kịch bản nghiệm thu (Acceptance Scenarios) của module **TRN-03 Ghi nhận nhận hàng và vận chuyển**.

---

## 1. Yêu cầu Tiên quyết & Thiết lập (Prerequisites)

1. Đã cài đặt môi trường Python 3.11+ và các thư viện trong `requirements.txt`.
2. Cơ sở dữ liệu SQLite dev đã được nạp dữ liệu mẫu ban đầu qua `src/core/seed.py`.
3. Server Uvicorn đang chạy hoặc có thể chạy tự động trong test suite qua `TestClient`.

---

## 2. Kiểm thử Tự động (Automated Tests)

Chạy kiểm thử riêng cho TRN-03:

```powershell
# Chạy unit tests cho logic nhận hàng và chuyển trạng thái
pytest tests/unit/test_pickup.py -v

# Chạy contract test cho OpenAPI endpoints
pytest tests/contract/test_pickup_api.py -v

# Chạy integration test kiểm tra trọn vẹn vòng đời chuyển đổi trạng thái
pytest tests/integration/test_trip_transitions.py -v
```

Chạy toàn bộ test suite để đảm bảo không có regression:

```powershell
pytest tests/ -v
```

---

## 3. Các Kịch bản Nghiệm thu Thực tế (Manual & E2E Acceptance Scenarios)

### Kịch bản 1: Nhận hàng hợp lệ và kiểm tra chuyển trạng thái Booking (MVP)
1. Đăng nhập hệ thống bằng tài khoản Điều phối viên (`dsp` / `password123`).
2. Điều hướng tới danh sách chuyến hàng tại `/trips`.
3. Chọn một chuyến hàng đang ở trạng thái `ASSIGNED` (ví dụ `ORDER-2026-FUT99`).
4. Nhấn nút **"Xác Nhận Nhận Hàng"** (`/trips/{id}/pickup`).
5. Nhập các thông tin:
   - Thời điểm nhận hàng thực tế: Giờ hiện tại hoặc trước đó.
   - Người bàn giao: `Nguyễn Văn Kho`.
   - Khối lượng hàng thực tế: Nhập giá trị nhỏ hơn hoặc bằng tải trọng của xe được phân công.
   - Tình trạng hàng hóa: `Nguyên đai nguyên kiện`.
6. Nhấn **"Xác Nhận Đã Nhận Hàng"**:
   - **Kỳ vọng**: Chuyến hàng chuyển trạng thái sang `PICKED_UP`.
   - Kiểm tra tại `/schedule`: Toàn bộ booking của xe và tài xế tương ứng chuyển từ `CONFIRMED` sang `IN_PROGRESS`.
   - Thao tác Đổi/Hủy phân công xe bị khóa hoàn toàn.

---

### Kịch bản 2: Từ chối Nhận hàng do Vượt tải trọng Thực tế (BR-06)
1. Trên màn hình ghi nhận nhận hàng của chuyến hàng được gán xe tải trọng 5,000 kg.
2. Nhập khối lượng thực tế cân được là `5,200` kg.
3. Quan sát giao diện:
   - Viền ô nhập liệu chuyển sang màu đỏ cảnh báo quá tải.
   - Nút xác nhận bị vô hiệu hóa hoặc nếu submit form thì hệ thống trả về mã lỗi 400.
4. Chuyến hàng vẫn giữ nguyên trạng thái `ASSIGNED`.
5. Điều phối viên bấm nút quay lại và thực hiện đổi xe sang xe tải trọng lớn hơn (ví dụ 8,000 kg) tại màn hình điều phối `/trips/{id}/dispatch`.

---

### Kịch bản 3: Từ chối Nhận hàng do Nguồn lực đang bận việc khác (BR-09)
1. Xe tải A hoặc Tài xế B đang thực hiện Chuyến 1 (trạng thái `IN_PROGRESS`).
2. Chuyến 2 cũng đã được phân công Xe tải A hoặc Tài xế B (ở trạng thái `ASSIGNED`).
3. Điều phối viên cố gắng bấm xác nhận nhận hàng cho Chuyến 2.
4. **Kỳ vọng**: Hệ thống từ chối xác nhận với thông báo lỗi rõ ràng theo quy tắc BR-09: *"Xe tải hoặc tài xế đang thực hiện một chuyến hàng khác chưa hoàn tất, không thể nhận hàng chuyến này."*
5. Trạng thái Chuyến 2 vẫn giữ nguyên là `ASSIGNED`.

---

### Kịch bản 4: Xe Khởi hành và Chuyển sang `IN_TRANSIT`
1. Với chuyến hàng đã ở trạng thái `PICKED_UP`.
2. Điều phối viên nhấn nút **"Khởi Hành"** hoặc nhập form chuyển trạng thái di chuyển.
3. Nhập thời điểm xuất phát thực tế (phải $\ge$ thời điểm nhận hàng).
4. Xác nhận:
   - Trạng thái chuyến chuyển thành `IN_TRANSIT`.
   - Dòng thời gian lịch sử lưu vết mốc xuất phát kèm thời điểm thực tế và thời điểm ghi nhận hệ thống.

---

### Kịch bản 5: Phân quyền Tra cứu Dòng thời gian (RBAC & Audit Trail)
1. Đăng xuất và đăng nhập bằng tài khoản Kinh doanh (`sal` / `password123`).
2. Vào chi tiết chuyến hàng:
   - Xem được đầy đủ dòng thời gian (Timeline) các mốc `ASSIGNED`, `PICKED_UP`, `IN_TRANSIT` cùng người bàn giao và khối lượng.
   - Các nút cập nhật mốc nhận hàng, xuất phát hoàn toàn bị ẩn hoặc vô hiệu hóa.
3. Nếu cố tình gửi request POST cập nhật mốc bằng công cụ ngoài, hệ thống trả về HTTP 403 Forbidden.
