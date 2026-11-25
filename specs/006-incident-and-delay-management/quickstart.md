# Quickstart Guide: TRN-05 Quản lý sự cố và chậm tiến độ (Incident & Delay Management)

**Feature**: TRN-05 Quản lý sự cố và chậm tiến độ  
**Spec**: [spec.md](spec.md) | **Contracts**: [contracts/incident-api.yaml](contracts/incident-api.yaml)  
**Date**: 2026-11-25

Hướng dẫn thực thi và kiểm thử nhanh các kịch bản của phân hệ TRN-05 bằng cả giao diện Web (Jinja2/Bootstrap) và API endpoints.

---

## 1. Chuẩn Bị Môi Trường & Dữ Liệu Kiểm Thử

Khởi động ứng dụng FastAPI:
```bash
uvicorn src.main:app --reload --port 8000
```
Tài khoản kiểm thử mặc định:
- **Điều phối viên (DSP)**: `dsp_test` / mật khẩu: `password123` (Có toàn quyền ghi nhận sự cố, đóng sự cố, gia hạn lịch).
- **Kinh doanh (SAL)**: `sal_test` / mật khẩu: `password123` (Chỉ xem, bị chặn ghi với HTTP 403 Forbidden).

---

## 2. Kịch Bản 1: Lập Biên Bản Sự Cố & Đóng Sự Cố (User Story 1 - MVP)

### Bước 1: Điều phối viên lập biên bản sự cố
1. Đăng nhập với tài khoản `dsp_test` tại `/login`.
2. Truy cập chi tiết một chuyến hàng đang ở trạng thái `IN_TRANSIT` (ví dụ: `/trips/1`).
3. Bấm nút **"Báo Cáo Sự Cố"** (hoặc mở Modal Báo Cáo Sự Cố).
4. Điền các thông tin:
   - **Loại sự cố**: Chọn `VEHICLE_BREAKDOWN` (Hỏng hóc phương tiện).
   - **Thời điểm phát sinh**: Chọn thời điểm thực tế (ví dụ: `2026-11-25 14:00`).
   - **Mô tả chi tiết**: "Xe bị nổ lốp sau trên cao tốc Pháp Vân - Cầu Giẽ, đang chờ đội cứu hộ".
   - **Người phụ trách xử lý**: "Tài xế Nguyễn Văn A & Cứu hộ cao tốc (0912.345.678)".
   - **Dự kiến khắc phục**: `2026-11-25 15:30`.
5. Bấm **"Gửi Báo Cáo Sự Cố"**.

**Kỳ vọng**:
- Biên bản sự cố xuất hiện trong bảng "Nhật Ký Sự Cố Chuyến Hàng" với badge màu đỏ `OPEN`.
- Trạng thái chuyến hàng (`trip.status`) **vẫn giữ nguyên `IN_TRANSIT`** (không bị đổi trạng thái).
- Cước phí chuyến hàng không bị thay đổi.
- Dòng thời gian ghi nhận sự kiện `ISSUE_LOGGED`.

### Bước 2: Đóng sự cố khi hoàn tất khắc phục
1. Tại bảng "Nhật Ký Sự Cố Chuyến Hàng", tại dòng sự cố `OPEN`, bấm nút **"Giải Quyết"**.
2. Nhập kết quả xử lý: "Đội cứu hộ đã thay xong lốp dự phòng, xe đã tiếp tục lăn bánh an toàn".
3. Bấm **"Xác Nhận Giải Quyết"**.

**Kỳ vọng**:
- Trạng thái sự cố chuyển sang `RESOLVED` (màu xanh lá).
- Cảnh báo sự cố đang mở trên chuyến hàng được tắt.
- Dòng thời gian ghi nhận sự kiện `ISSUE_RESOLVED`.

---

## 3. Kịch Bản 2: Phát Hiện & Hiển Thị Cờ Quá Hạn Vận Hành (User Story 2)

1. Chọn một chuyến hàng chưa kết thúc (trạng thái `ASSIGNED`, `PICKED_UP`, hoặc `IN_TRANSIT`) có thời điểm kết thúc dự kiến `estimated_end_time` nhỏ hơn thời điểm hiện tại.
2. Mở danh mục chuyến hàng tại `/trips`.

**Kỳ vọng**:
- Chuyến hàng hiển thị badge cảnh báo nổi bật: `<span class="badge bg-danger"><i class="bi bi-alarm-fill me-1"></i> Quá hạn</span>`.
- Trong chi tiết chuyến hàng, hiển thị khung thông báo màu đỏ: *"Chuyến hàng đã quá hạn cam kết vận hành (Dự kiến: dd/mm/yyyy hh:mm). Vui lòng kiểm tra tiến độ với tài xế hoặc cập nhật gia hạn lịch trình."*
- Khi chuyến hàng được ghi nhận giao thành công (`DELIVERED`) hoặc đóng hoàn tất (`COMPLETED`), cờ cảnh báo quá hạn tự động biến mất.

---

## 4. Kịch Bản 3: Gia Hạn Lùi Lịch Dự Kiến & Cảnh Báo Xung Đột Lịch Tương Lai (User Story 3)

### Tình huống kiểm thử
- Chuyến hàng `TRIP-A` có xe tải `29C-123.45` đang thực hiện, lịch kết thúc ban đầu là `17:00`.
- Chuyến hàng `TRIP-B` đã được phân công cho cùng xe tải `29C-123.45` với lịch bắt đầu lúc `18:00`.
- `TRIP-A` gặp sự cố ùn tắc, điều phối viên cần gia hạn mốc kết thúc của `TRIP-A` thành `19:30` (chồng lấn vào khung giờ của `TRIP-B`).

### Các bước thực hiện
1. Tại chi tiết chuyến hàng `TRIP-A`, bấm nút **"Gia Hạn Lịch Trình"**.
2. Nhập mốc thời gian kết thúc dự kiến mới: `19:30`.
3. Nhập lý do gia hạn: "Sự cố kẹt xe và hỏng lốp, kéo dài thời gian hoàn thành".
4. Bấm **"Xác Nhận Gia Hạn"**.

**Kỳ vọng**:
- Hệ thống **chấp nhận cập nhật** mốc `estimated_end_time = 19:30` cho `TRIP-A` và mở rộng thời gian kết thúc booking của `TRIP-A`.
- Hệ thống hiển thị **Modal/Thông báo cảnh báo xung đột (HTTP 409 Conflict)**: Liệt kê chi tiết chuyến `TRIP-B` bị trùng lịch xe tải `29C-123.45` từ `18:00 - 19:30`.
- Hệ thống hướng dẫn điều phối viên gỡ hoặc đổi phân công cho chuyến `TRIP-B`.
- Quy tắc **BR-09** tiếp tục có hiệu lực: Tài xế và xe tải của `TRIP-A` chưa hoàn tất (`IN_PROGRESS`) thì không thể bấm nhận hàng cho `TRIP-B`.
- Dòng thời gian ghi nhận sự kiện `SCHEDULE_DELAYED`.

---

## 5. Kịch Bản 4: Kiểm Soát Phân Quyền RBAC (User Story 5)

1. Đăng xuất và đăng nhập lại với tài khoản `sal_test` (vai trò `SAL`).
2. Truy cập `/trips`:
   - Người dùng `SAL` xem được danh sách chuyến hàng, xem được cờ quá hạn `DELAYED` và số sự cố.
3. Vào xem chi tiết chuyến hàng `/trips/1`:
   - Xem được đầy đủ thông tin sự cố, người xử lý, kết quả giải quyết.
   - **Các nút "Báo Cáo Sự Cố", "Giải Quyết", "Gia Hạn Lịch Trình" hoàn toàn bị ẩn**.
4. Sử dụng API client (curl/Postman) gửi request `POST /api/v1/trips/1/issues` với cookie của `sal_test`:
   - Hệ thống từ chối với mã lỗi **HTTP 403 Forbidden**: `{"detail": "Quyền truy cập bị từ chối. Thao tác yêu cầu vai trò: ['DSP']"}`.
