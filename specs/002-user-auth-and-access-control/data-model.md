# Data Model Specification: 002-user-auth-and-access-control

**Feature**: `002-user-auth-and-access-control`  
**Date**: 2026-11-23  
**Status**: Draft  

---

## 1. Thực thể (Entities) & Thuộc tính

### 1.1. Bảng `users` (Danh mục Tài khoản Người dùng)

Lưu trữ thông tin tài khoản đăng nhập, mật khẩu băm, họ tên hiển thị và vai trò phân quyền.

| Tên trường | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Khóa chính định danh người dùng |
| `username` | `VARCHAR(50)` | `NOT NULL, UNIQUE, INDEX` | Tên đăng nhập duy nhất (ví dụ: `dsp_user`) |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | Chuỗi băm mật khẩu bảo mật (bcrypt) |
| `full_name` | `VARCHAR(100)` | `NOT NULL` | Họ và tên đầy đủ của người dùng |
| `role` | `VARCHAR(20)` | `NOT NULL, DEFAULT 'DSP'` | Vai trò người dùng: `DSP`, `SAL`, `MGR` |
| `is_active` | `BOOLEAN` | `NOT NULL, DEFAULT TRUE` | Trạng thái hoạt động (`TRUE`: Cho phép đăng nhập) |
| `created_at` | `DATETIME` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Thời điểm tạo tài khoản |
| `updated_at` | `DATETIME` | `NOT NULL, DEFAULT CURRENT_TIMESTAMP` | Thời điểm cập nhật cuối cùng |

---

## 2. Enums & Ràng buộc Kiểm tra (Constraints)

### 2.1. Enum Vai trò (`UserRole`)
```python
class UserRole(str, enum.Enum):
    DSP = "DSP"   # Dispatcher - Điều phối viên
    SAL = "SAL"   # Sales - Nhân viên kinh doanh (Chỉ đọc)
    MGR = "MGR"   # Manager - Quản lý / Giám đốc
```

### 2.2. Check Constraints
- `ck_user_role_valid`: `CHECK (role IN ('DSP', 'SAL', 'MGR'))`
- `ck_username_length`: `CHECK (length(username) >= 3)`

---

## 3. Ma trận Phân quyền theo Vai trò (Permission Matrix)

| Chức năng / Hành động | `DSP` (Điều phối) | `SAL` (Kinh doanh) | `MGR` (Quản lý) | Khách vãng lai |
| :--- | :---: | :---: | :---: | :---: |
| Xem Tổng quan Dashboard (`/dashboard`) | ✅ Cho phép | ✅ Cho phép | ✅ Cho phép | ❌ Redirect `/login` |
| Xem danh mục Đội Xe & Tài Xế | ✅ Cho phép | ✅ Cho phép | ✅ Cho phép | ❌ Redirect `/login` |
| Thêm mới / Chỉnh sửa Xe & Tài Xế | ✅ Cho phép | 🚫 Chặn 403 | 🚫 Chặn 403 | ❌ Redirect `/login` |
| Đổi trạng thái Xe / Tài Xế (`PATCH`) | ✅ Cho phép | 🚫 Chặn 403 | 🚫 Chặn 403 | ❌ Redirect `/login` |
| Xóa Xe / Tài Xế (`DELETE`) | ✅ Cho phép (Kiểm tra Soft-Delete) | 🚫 Chặn 403 | 🚫 Chặn 403 | ❌ Redirect `/login` |
| Điều phối chuyến xe (TRN-02) | ✅ Cho phép | 🚫 Chặn 403 | 🚫 Chặn 403 | ❌ Redirect `/login` |

---

## 4. Dữ liệu mẫu khởi tạo sẵn (Pre-seeded Accounts)

| Username | Plain Password | Role | Tên hiển thị |
| :--- | :--- | :--- | :--- |
| `dsp_user` | `password123` | `DSP` | Nguyễn Văn Điều Phối |
| `sal_user` | `password123` | `SAL` | Trần Thị Kinh Doanh |
| `mgr_user` | `password123` | `MGR` | Lê Quản Lý Đội Xe |
