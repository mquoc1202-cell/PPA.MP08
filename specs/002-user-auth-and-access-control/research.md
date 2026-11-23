# Research & Technical Decisions: 002-user-auth-and-access-control

**Feature**: `002-user-auth-and-access-control`  
**Date**: 2026-11-23  
**Status**: Completed  

---

## 1. Cơ chế Quản lý Phiên làm việc (Session-Based Cookie Authentication)

### Vấn đề cần giải quyết
Hệ thống cần xác thực người dùng trên cả giao diện Web Server-Side Rendering (Jinja2) và REST API. Theo Hiến pháp dự án (`constitution.md`) và quy định bắt buộc trong `AGENTS.md`: "Dùng Session-Based Cookie Authentication (HTTP-Only, Secure, SameSite). TUYỆT ĐỐI KHÔNG dùng JWT nếu chưa được thống nhất."

### Quyết định kỹ thuật
- Sử dụng `SessionMiddleware` tích hợp sẵn của Starlette / FastAPI với cơ chế Signed Cookie:
  - Tên Cookie: `freight_session`
  - Khóa ký mã hóa: `settings.SECRET_KEY`
  - Thuộc tính an toàn: `httponly=True`, `samesite="lax"`, `max_age=86400` (24 giờ)
- Cấu trúc dữ liệu lưu trong session:
  ```python
  request.session["current_user"] = {
      "id": user.id,
      "username": user.username,
      "full_name": user.full_name,
      "role": user.role
  }
  ```
- **Lý do chọn**: Đảm bảo bảo mật tối đa trước các cuộc tấn công XSS (do JS không đọc được HTTP-Only cookie), tương thích hoàn hảo với mô hình SSR của Jinja2, không cần quản lý bảng Refresh Token phức tạp.

---

## 2. Mã hóa & Băm mật khẩu (Password Hashing)

### Vấn đề cần giải quyết
TUYỆT ĐỐI KHÔNG lưu mật khẩu bản rõ trong cơ sở dữ liệu. Cần giải thuật băm một chiều bảo mật cao có muối (salt) tự sinh.

### Quyết định kỹ thuật
- Sử dụng thư viện `bcrypt` tiêu chuẩn công nghiệp:
  - Băm mật khẩu: `bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')`
  - Kiểm tra mật khẩu: `bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))`
- **Lý do chọn**: `bcrypt` có chi phí tính toán có thể điều chỉnh (*cost factor*), tự động chống lại các cuộc tấn công Rainbow Table nhờ salt ngẫu nhiên 128-bit, là chuẩn mực bảo mật cho tài khoản người dùng doanh nghiệp.

---

## 3. Kiến trúc Phân quyền theo vai trò (Role-Based Access Control - RBAC)

### Vấn đề cần giải quyết
Theo tài liệu vận tải gốc `03_Freight_Transportation.pdf`:
- `DSP` (Điều phối viên): Có quyền tạo/sửa xe, tài xế, điều phối đơn vận chuyển.
- `SAL` (Nhân viên kinh doanh) & `MGR` (Quản lý): Chỉ có quyền tra cứu (Read-only), không được phép điều phối hoặc đổi trạng thái.

### Quyết định kỹ thuật
- **FastAPI Dependencies bảo vệ**:
  - `get_current_user`: Trích xuất thông tin người dùng từ `request.session`. Nếu chưa đăng nhập:
    - Với Web Request: Chuyển hướng `RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)`.
    - Với API Request: Trả mã HTTP 401 Unauthorized.
  - `require_role(allowed_roles: List[str])`: Kiểm tra vai trò của `current_user`:
    - Nếu vai trò hợp lệ: Cho phép tiếp tục xử lý.
    - Nếu không đủ thẩm quyền (ví dụ `SAL` cố tình gọi API tạo xe):
      - Với Web Request: Render giao diện `templates/error/403.html` với HTTP 403.
      - Với API Request: Trả JSON `{success: False, error: "Bạn không có quyền thực hiện thao tác này.", ...}` với HTTP 403 Forbidden.
- **Tầng Template Jinja2**:
  - Truyền `current_user` vào context.
  - Điều khiển hiển thị:
    ```jinja2
    {% if current_user and current_user.role == 'DSP' %}
      <a href="/admin/trucks/create" class="btn btn-primary">Thêm Xe Mới</a>
    {% endif %}
    ```

---

## 4. Dữ liệu tài khoản khởi tạo mẫu (Demo Accounts)

### Quyết định kỹ thuật
Trong hàm `seed_initial_data(db)`, tự động nạp sẵn 3 tài khoản demo phục vụ kiểm thử:
1. `dsp_user` / `password123` ➔ Role: `DSP` (Điều phối viên)
2. `sal_user` / `password123` ➔ Role: `SAL` (Kinh doanh - Read-only)
3. `mgr_user` / `password123` ➔ Role: `MGR` (Quản lý - Báo cáo)

Tại trang `/login`, cung cấp sẵn thanh chọn nhanh (1-Click Fill) để người dùng có thể chuyển đổi vai trò ngay tức thì mà không phải nhớ hay gõ lại mật khẩu.
