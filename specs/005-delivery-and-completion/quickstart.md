# Quickstart Validation Guide: TRN-04 Xác nhận giao hàng và hoàn tất

**Branch**: `005-delivery-and-completion` | **Date**: 2026-11-25 | **Feature**: [spec.md](spec.md)

Tài liệu này cung cấp hướng dẫn chạy thử nghiệm và kiểm thử nghiệm thu tính năng TRN-04 (Giao hàng, chứng từ POD, xử lý sự cố, hoàn tất và giải phóng tài nguyên) trên cả giao diện Web SSR và REST API.

---

## 1. Yêu Cầu Tiền Đề (Prerequisites)

- **Môi trường:** Python 3.11+ (hiện hành: Python 3.13)
- **Cơ sở dữ liệu:** SQLite `freight_dev.db` đã khởi tạo và nạp dữ liệu mẫu
- **Tài khoản kiểm thử:**
  - Điều phối viên (DSP): `dsp` / `password123` (Đầy đủ quyền thao tác)
  - Nhân viên kinh doanh (SAL): `sal` / `password123` (Quyền chỉ đọc)
  - Quản lý đội xe (MGR): `mgr` / `password123` (Quyền chỉ đọc)

---

## 2. Khởi Động Máy Chủ

Chạy lệnh khởi động máy chủ FastAPI từ thư mục gốc dự án:
```powershell
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Giao diện Web:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Tài liệu Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 3. Các Kịch Bản Xác Thực Nghiệm Thu (Validation Scenarios)

### Kịch Bản 1: Giao Hàng Thành Công kèm Tải Tệp Bằng Chứng POD (`IN_TRANSIT` ➔ `DELIVERED`)

1. **Chuẩn bị:** Chọn chuyến hàng đang ở trạng thái `IN_TRANSIT` (ví dụ mã `TRIP-2026-TRNST`).
2. **Thao tác Web:**
   - Đăng nhập với tài khoản `dsp` / `password123`.
   - Vào danh mục chuyến hàng tại `/trips`, bấm nút **"Giao Hàng"** hoặc mở trang chi tiết `/trips/{id}` chọn **"Ghi Nhận Giao Hàng"**.
   - Tại màn hình `/trips/{id}/deliver`:
     - Nhập thời điểm giao hàng thực tế: `2026-11-25 14:00` (đảm bảo $\ge$ thời điểm nhận hàng `07:30`).
     - Nhập người nhận: `Bác sĩ Nguyễn Văn Cường - Bệnh viện Đa khoa Tỉnh Bình Thuận`.
     - Kết quả: Chọn `Giao thành công`.
     - Tải lên tệp bằng chứng: Chọn 1 ảnh chụp biên bản bàn giao (`bien_ban_pod.jpg` hoặc `.pdf`).
     - Bấm **"Xác Nhận Giao Hàng"**.
3. **Kỳ vọng:**
   - Hệ thống chuyển hướng về `/trips/{id}` với thông báo thành công.
   - Huy hiệu trạng thái chuyển sang màu xanh dương `DELIVERED`.
   - Mục "Bằng chứng bàn giao (POD)" hiển thị tên tệp, dung lượng và nút xem/tải về.
   - Dòng thời gian hiển thị sự kiện `DELIVERY_CONFIRMED`.

---

### Kịch Bản 2: Từ Chối Giao Hàng Khi Thiếu Tệp Chứng Từ hoặc Sai Thời Gian

1. **Kiểm tra thiếu bằng chứng:**
   - Tại form giao hàng, nhập đầy đủ người nhận nhưng không chọn tệp bằng chứng nào.
   - Bấm gửi form.
   - **Kỳ vọng:** Hệ thống từ chối (HTTP 400), giữ nguyên form và hiển thị cảnh báo đỏ: *"Bắt buộc phải tải lên ít nhất một tệp chứng từ giao hàng (POD)"*. Chuyến hàng vẫn ở `IN_TRANSIT`.
2. **Kiểm tra sai mốc thời gian:**
   - Nhập thời điểm giao hàng `2026-11-25 05:00` (trước thời điểm nhận hàng `07:30`).
   - **Kỳ vọng:** Hệ thống từ chối (HTTP 400), cảnh báo *"Thời điểm giao hàng không được trước thời điểm nhận hàng"*.

---

### Kịch Bản 3: Giao Hàng Thất Bại & Khởi Tạo Biên Bản Sự Cố

1. **Thao tác:**
   - Tại form `/trips/{id}/deliver`, chọn kết quả: `Giao không thành công`.
   - Nhập lý do: `Khách hàng từ chối nhận do bao bì rách và yêu cầu đổi hàng`.
   - Đính kèm ảnh chụp kiện hàng rách (tùy chọn).
   - Bấm **"Ghi Nhận Sự Cố Giao Hàng"**.
2. **Kỳ vọng:**
   - Chuyến hàng **giữ nguyên trạng thái `IN_TRANSIT`** (tuyệt đối không chuyển sang `DELIVERED`).
   - Một bản ghi sự cố mới xuất hiện trong mục "Nhật ký sự cố" của chuyến với trạng thái `OPEN`.
   - Nút hoàn tất chuyến bị vô hiệu hóa vì chuyến chưa đạt mốc `DELIVERED`.

---

### Kịch Bản 4: Chốt Hoàn Tất Chuyến Hàng & Giải Phóng Tài Nguyên (`DELIVERED` ➔ `COMPLETED`)

1. **Thao tác:**
   - Trên màn hình chi tiết chuyến hàng đã ở `DELIVERED` (từ Kịch bản 1), bấm nút **"Hoàn Tất Chuyến Hàng"**.
   - Modal xác nhận mở ra:
     - Nhập thời điểm hoàn tất: Thời điểm hiện tại hoặc sau thời điểm giao hàng (ví dụ: `2026-11-25 15:30`).
     - Bấm **"Xác Nhận Đóng Chuyến"**.
2. **Kỳ vọng:**
   - Trạng thái chuyến hàng chuyển sang màu xanh lá `COMPLETED`.
   - Lịch chiếm dụng `ResourceBooking` của cả Xe tải và Tài xế đổi sang `COMPLETED`.
   - Mở màn hình tạo/điều phối chuyến mới cho cùng xe tải hoặc tài xế này: hệ thống cho phép ghi nhận nhận hàng mà không bị chặn bởi lỗi xung đột bận việc BR-09!

---

### Kịch Bản 5: Kiểm Soát Phân Quyền Vai Trò (RBAC)

1. **Thao tác:**
   - Đăng xuất và đăng nhập bằng tài khoản `sal` / `password123`.
   - Truy cập trang chi tiết chuyến hàng `/trips/{id}`.
2. **Kỳ vọng:**
   - Xem được toàn bộ thông tin chi tiết, ảnh chứng từ POD, dòng thời gian và nhật ký sự cố.
   - Các nút thao tác "Giao Hàng", "Hoàn Tất Chuyến" bị ẩn.
   - Nếu cố tình gửi yêu cầu `POST /trips/{id}/deliver` hoặc `POST /trips/{id}/complete`, hệ thống trả về mã lỗi `403 Forbidden` và render trang lỗi 403.

---

## 4. Kiểm Thử Tự Động (Automated Testing)

Chạy toàn bộ bộ kiểm thử tự động của TRN-04:
```powershell
pytest tests/unit/test_delivery.py tests/contract/test_delivery_api.py tests/integration/test_delivery_lifecycle.py -v
```
Kỳ vọng: 100% test cases đạt trạng thái `PASSED`.
