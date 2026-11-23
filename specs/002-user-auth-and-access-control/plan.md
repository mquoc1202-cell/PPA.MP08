# Implementation Plan: 002-user-auth-and-access-control

**Branch**: `002-user-auth-and-access-control` | **Date**: 2026-11-23 | **Spec**: [spec.md](file:///d:/PPA.MP08_GROUP3/specs/002-user-auth-and-access-control/spec.md)

**Input**: Feature specification from `specs/002-user-auth-and-access-control/spec.md`

## Summary

Module `002-user-auth-and-access-control` thiết lập hạ tầng định danh, phiên làm việc an toàn và phân quyền người dùng theo vai trò (Role-Based Access Control - RBAC) cho toàn bộ hệ thống Freight ERP.
Cách tiếp cận kỹ thuật:
- Tạo bảng `users` lưu trữ tài khoản, mật khẩu băm bảo mật bằng `bcrypt` và vai trò (`DSP`, `SAL`, `MGR`).
- Tích hợp `SessionMiddleware` với Cookie HTTP-Only có chữ ký số an toàn (Signed Session Cookie), loại bỏ rủi ro rò rỉ token qua XSS.
- Xây dựng tầng Dependencies bảo vệ: `get_current_user` (xác thực đăng nhập) và `require_role` (kiểm tra quyền hạn).
- Phân tách quyền chặt chẽ: `DSP` có toàn quyền điều phối; `SAL` & `MGR` ở chế độ chỉ đọc (Read-only); từ chối các thao tác ghi trái quyền bằng HTTP 403 Forbidden.
- Xây dựng giao diện trang đăng nhập `/login` đồng bộ chuẩn thiết kế `frontend/DESIGN.md`, tích hợp thanh 1-Click Demo Accounts phục vụ kiểm thử nhanh.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, Starlette `SessionMiddleware`, `bcrypt`, Pydantic v2, SQLAlchemy, Jinja2  
**Storage**: SQLite (Local development / Pytest isolation) qua SQLAlchemy ORM  
**Testing**: `pytest`, `httpx` (FastAPI TestClient với Cookie Session)  
**Target Platform**: Windows / Linux server, Modern Web Browsers  
**Project Type**: Web Application & REST API (FastAPI backend + Jinja2 Bootstrap 5 SSR frontend)  
**Performance Goals**:
- Thời gian xác thực đăng nhập: `< 50ms`
- Kiểm tra quyền trong Dependency: `< 1ms` (In-memory session check)
**Constraints**:
- Tuân thủ nghiêm ngặt Hiến pháp dự án (`constitution.md`) và `AGENTS.md`.
- Tuyệt đối không dùng JWT khi chưa có thống nhất.
- Tuyệt đối không lưu mật khẩu dạng bản rõ.
- Masking lỗi và ghi log đầy đủ bằng Python `logging`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc Hiến pháp | Đánh giá thiết kế | Kết quả |
| :--- | :--- | :---: |
| **I. Layered Architecture** | Tách biệt tuyệt đối: `core/security.py` (băm & dependencies), `models/user.py`, `repositories/user_repo.py`, `services/auth_service.py`, `web/auth.py` và `api/v1/auth.py`. | **PASS** |
| **II. State Machine & Audit Trail** | Tài khoản có trường `is_active` để khóa tài khoản (soft-deactivate), bảo lưu lịch sử người thực hiện thao tác. | **PASS** |
| **III. Strict Concurrency & ACID** | Đăng nhập là thao tác đọc an toàn; cập nhật thông tin user tuân thủ transaction SQLAlchemy. | **PASS** |
| **IV. Test-Driven Verification (TDD)** | Bộ test tự động `pytest` bao phủ: đăng nhập đúng, sai mật khẩu, đăng xuất, chuyển hướng khi chưa login, và kiểm tra quyền RBAC (DSP vs SAL) chặn mã 403. | **PASS** |
| **V. Security & Observability** | Mật khẩu băm bằng `bcrypt`, session HTTP-Only cookie, không ghi log thông tin nhạy cảm. | **PASS** |

## Project Structure

### Documentation (this feature)

```text
specs/002-user-auth-and-access-control/
├── plan.md              # Kế hoạch triển khai kỹ thuật
├── research.md          # Quyết định kỹ thuật: Session Cookie, bcrypt, RBAC
├── data-model.md        # Đặc tả bảng users và ma trận phân quyền
├── quickstart.md        # Hướng dẫn kiểm thử thủ công và tự động
├── contracts/           # API Contracts OpenAPI 3.0
│   └── auth-api.yaml
└── tasks.md             # Danh sách atomic tasks (/speckit-tasks output)
```

### Source Code (repository root)

```text
src/
├── core/
│   ├── security.py         # Hàm băm bcrypt, verify password, dependencies get_current_user, require_role
├── models/
│   ├── user.py             # SQLAlchemy Model: User, UserRole Enum
├── schemas/
│   ├── auth.py             # Pydantic v2 schemas: LoginRequest, UserSession, UserResponse
├── repositories/
│   ├── user_repo.py        # Truy vấn bảng users theo username, ID
├── services/
│   ├── auth_service.py     # Nghiệp vụ xác thực username/password, kiểm tra active
├── api/
│   └── v1/
│       ├── auth.py         # REST API endpoints (/api/v1/auth/login, /logout, /me)
├── web/
│   ├── auth.py             # Web views SSR (/login, /logout)
├── templates/
│   ├── auth/
│   │   └── login.html      # Giao diện đăng nhập hiện đại + 1-Click Demo Accounts
│   └── error/
│       └── 403.html        # Trang cảnh báo không đủ quyền hạn (Forbidden)
└── main.py                 # Tích hợp SessionMiddleware và đăng ký routers mới

tests/
├── unit/
│   └── test_auth.py        # Test băm mật khẩu, verify login đúng/sai
└── integration/
    └── test_rbac.py        # Test bảo vệ URL & phân quyền DSP vs SAL (HTTP 403)
```

## Complexity Tracking

Không có vi phạm nguyên tắc Hiến pháp nào cần giải trình (*Zero Constitutional Violations*).
