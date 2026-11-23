# Quickstart & Validation Guide: 002-user-auth-and-access-control

Hướng dẫn kiểm thử và chạy thực nghiệm các kịch bản xác thực tài khoản và phân quyền người dùng (RBAC).

---

## 1. Môi trường yêu cầu (Prerequisites)

- Python 3.11+
- Thư viện bổ sung:
  ```text
  bcrypt>=5.0.0
  itsdangerous>=2.1.0
  ```

---

## 2. Kịch bản Kiểm thử Nghiệm thu (Acceptance Scenarios)

### Kịch bản 1: Đăng nhập thành công với tài khoản DSP
1. Mở trình duyệt tại [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login).
2. Nhập:
   - Tên đăng nhập: `dsp_user`
   - Mật khẩu: `password123`
   - Bấm **Đăng Nhập**.
3. **Kỳ vọng**: 
   - Chuyển hướng về `/dashboard`.
   - Trên thanh Top Navbar hiển thị: `Nguyễn Văn Điều Phối` kèm Badge `[DSP]`.
   - Truy cập trang [Quản lý Đội Xe](http://127.0.0.1:8000/admin/trucks) thấy đầy đủ các nút **Thêm Xe Mới**, **Sửa**, **Xóa**.

### Kịch bản 2: Đăng nhập với tài khoản SAL (Kinh doanh - Read-only)
1. Đăng xuất tài khoản cũ tại [http://127.0.0.1:8000/logout](http://127.0.0.1:8000/logout).
2. Tại `/login`, nhập:
   - Tên đăng nhập: `sal_user`
   - Mật khẩu: `password123`
3. **Kỳ vọng**:
   - Chuyển hướng về `/dashboard`.
   - Trên Navbar hiển thị: `Trần Thị Kinh Doanh` kèm Badge `[SAL]`.
   - Truy cập [Quản lý Đội Xe](http://127.0.0.1:8000/admin/trucks): Các nút **Thêm Xe Mới**, **Sửa**, **Xóa** hoàn toàn bị ẩn.
   - Nếu cố tình gõ URL [http://127.0.0.1:8000/admin/trucks/create](http://127.0.0.1:8000/admin/trucks/create) ➔ Hệ thống trả về giao diện cảnh báo **403 Forbidden: Bạn không có quyền truy cập chức năng này.**

### Kịch bản 3: Đăng nhập sai mật khẩu
1. Tại `/login`, nhập `dsp_user` và mật khẩu `sai_mat_khau`.
2. **Kỳ vọng**:
   - Render lại trang `/login` với status 400.
   - Hiển thị banner đỏ: "Tên đăng nhập hoặc mật khẩu không chính xác."
   - Giá trị `dsp_user` trong ô tên đăng nhập vẫn được giữ nguyên.

### Kịch bản 4: Đăng xuất và Bảo vệ URL nội bộ
1. Bấm nút **Đăng xuất**.
2. Thử truy cập trực tiếp [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard).
3. **Kỳ vọng**: Bị chuyển hướng ngay lập tức về `/login?next=%2Fdashboard`.

---

## 3. Chạy Kiểm Thử Tự Động (`pytest`)

```powershell
pytest tests/unit/test_auth.py tests/integration/test_rbac.py -v
```
Mục tiêu nghiệm thu: **100% tests PASS**.
