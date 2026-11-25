# Quickstart & Validation Guide: 003-trip-dispatch-and-conflict-management

**Feature**: `003-trip-dispatch-and-conflict-management` (TRN-02)  
**Date**: 2026-11-23  
**Status**: Ready  

---

## 1. Mục đích
Tài liệu hướng dẫn kiểm thử và xác thực thực tế 4 kịch bản cốt lõi của **TRN-02: Điều phối chuyến hàng và quản lý trùng lịch** thông qua REST API và Giao diện Web SSR.

---

## 2. Chuẩn bị Môi trường

1. **Khởi động Server**:
   ```sh
   python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. **Tài khoản kiểm thử**:
   - `dsp_user` / `password123` (Vai trò: `DSP` - Điều phối viên, có quyền thực hiện phân công)
   - `sal_user` / `password123` (Vai trò: `SAL` - Kinh doanh, chỉ xem, bị chặn ghi)

---

## 3. Kịch bản Xác thực Đầu cuối (End-to-End Scenarios)

### Kịch bản 1: Phân công Hợp lệ (Happy Path - US1)
- **Hành động**:
  1. Đăng nhập tài khoản `dsp_user`.
  2. Mở chuyến hàng `UNASSIGNED` có khối lượng hàng hóa `4,500 kg`.
  3. Phân công Xe tải `29C-123.45` (tải trọng `5,000 kg`, trạng thái `ACTIVE`) và Tài xế `TX001` (trạng thái `ACTIVE`) cho khung giờ ngày mai `08:00 - 17:00`.
- **Kỳ vọng**:
  - HTTP Status: `200 OK`.
  - Trạng thái chuyến chuyển sang `ASSIGNED`.
  - Tự động tạo 2 bản ghi `ResourceBooking` cho xe và tài xế với trạng thái `CONFIRMED`.

### Kịch bản 2: Từ chối Quá tải Trọng (Overweight Rejection - BR-06)
- **Hành động**:
  1. Chọn chuyến hàng có khối lượng `6,000 kg`.
  2. Cố tình phân công Xe tải `29C-123.45` (tải trọng `5,000 kg`).
- **Kỳ vọng**:
  - HTTP Status: `400 Bad Request`.
  - Thông báo lỗi: "Khối lượng hàng hóa (6,000 kg) vượt quá tải trọng của xe (5,000 kg)."
  - Chuyến hàng giữ nguyên trạng thái `UNASSIGNED`, không có bất kỳ booking nào được tạo.

### Kịch bản 3: Ngăn chặn Xung đột Trùng lịch & Tính Nguyên tử (Schedule Conflict & Atomicity - BR-07, BR-08)
- **Hành động**:
  1. Chọn chuyến hàng thứ 2 cần phân công từ `10:00 - 14:00` cùng ngày với Kịch bản 1.
  2. Chọn Xe tải `29C-123.45` (đã bị gán lịch ở Kịch bản 1) hoặc Tài xế `TX001`.
- **Kỳ vọng**:
  - HTTP Status: `409 Conflict`.
  - Thông báo lỗi: "Xe hoặc tài xế đã bị chiếm dụng trong khoảng thời gian này."
  - Dữ liệu trả về liệt kê chi tiết các booking bị xung đột.
  - **Tính nguyên tử**: Cả xe và tài xế đều không bị giữ lịch mới; chuyến giữ nguyên trạng thái `UNASSIGNED`.

### Kịch bản 4: Đổi hoặc Gỡ Phân công trước khi Nhận hàng (Reassign & Unassign - US2)
- **Hành động 4a (Đổi phân công)**:
  1. Với chuyến đang ở `ASSIGNED`, thực hiện đổi sang Xe tải `29H-567.89` (tải trọng `8,000 kg`, còn trống lịch).
  2. Kỳ vọng: Lịch cũ của xe `29C-123.45` được giải phóng (`CANCELLED`); xe mới được tạo booking mới; chuyến vẫn ở `ASSIGNED`.
- **Hành động 4b (Khóa can thiệp khi đã nhận hàng)**:
  1. Giả lập chuyến đã chuyển sang trạng thái `PICKED_UP`.
  2. Gọi lệnh đổi xe hoặc hủy phân công.
  3. Kỳ vọng: HTTP Status `400 Bad Request` - "Chuyến hàng đã nhận hàng hoặc đang vận chuyển, không được phép can thiệp phân công."

---

## 4. Chạy Kiểm thử Tự động (Automated Test Verification)

```sh
pytest tests/unit/test_dispatch.py tests/integration/test_dispatch_lifecycle.py -v
```
- **Tiêu chuẩn nghiệm thu**: 100% test cases đạt trạng thái `PASSED`.
