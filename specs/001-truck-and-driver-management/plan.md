# Implementation Plan: TRN-01 Quản lý xe và tài xế

**Branch**: `001-truck-and-driver-management` | **Date**: 2026-11-23 | **Spec**: [spec.md](file:///d:/PPA.MP08_GROUP3/specs/001-truck-and-driver-management/spec.md)

**Input**: Feature specification from `specs/001-truck-and-driver-management/spec.md`

## Summary

Module TRN-01 chịu trách nhiệm thiết lập và quản lý dữ liệu phương tiện (`Truck`) và tài xế (`Driver`) phục vụ hoạt động vận tải. 
Cách tiếp cận kỹ thuật:
- Chuẩn hóa biển số xe bằng thuật toán Regex để triệt tiêu trùng lặp và lưu trữ chỉ mục duy nhất (`normalized_plate`).
- Kiểm tra tính hợp lệ của tải trọng (`capacity_kg > 0`) ở cả tầng Schema Pydantic và Check Constraint của CSDL.
- Tính toán lịch rảnh/bận và kiểm tra xung đột động thông qua bảng `ResourceBooking`; nghiêm cấm dùng cờ tĩnh.
- Triệt để cấm xóa cứng (Hard Delete) các nguồn lực đã có lịch sử giao dịch nhằm tuân thủ nguyên tắc Immutable Audit Trail.
- Xây dựng theo kiến trúc phân tầng sạch (Clean Layered Architecture): Router ➔ Service ➔ Repository ➔ Models, xử lý lỗi tập trung và bảo vệ dữ liệu với Session Authentication.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI (v0.110+), Pydantic v2 (v2.6+), SQLAlchemy (v2.0+), Jinja2 (v3.1+), Uvicorn  
**Storage**: SQLite (Local development / Pytest isolation) và tương thích SQL Server 2022 / PostgreSQL qua SQLAlchemy ORM  
**Testing**: `pytest` (v8.0+), `httpx` (FastAPI TestClient)  
**Target Platform**: Windows / Linux server, Modern Web Browsers  
**Project Type**: Web Application & REST API (FastAPI backend + Jinja2 Bootstrap 5 SSR frontend)  
**Performance Goals**:
- Chuẩn hóa biển số xe & tra cứu trùng lặp: `< 20ms`
- Kiểm tra lịch xung đột trong tương lai: `< 50ms` (O(log N) với chỉ mục hợp phần)
- Phản hồi API CRUD: `< 100ms`
**Constraints**:
- Tuân thủ tuyệt đối 5 nguyên tắc Hiến pháp dự án (`constitution.md`).
- Bắt buộc dùng `logging` chuẩn, nghiêm cấm `print()`.
- Định dạng JSON trả về chuẩn: `{"success": bool, "data": Any, "error": str | None, "meta": dict}`.
- Kiểm tra quyền truy cập và xác thực dựa trên Session Cookie.
**Scale/Scope**:
- 50+ đầu xe, 100+ tài xế, hàng nghìn lượt booking/trips.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc Hiến pháp | Đánh giá thiết kế | Kết quả |
| :--- | :--- | :---: |
| **I. Layered Architecture** | Tách biệt tuyệt đối: `api/` (Routers, Schemas), `services/` (Business Logic), `repositories/` (SQLAlchemy queries), `models/` (DB Entities). Không viết SQL trong Controller/Router hay Service. | **PASS** |
| **II. State Machine & Audit Trail** | Trạng thái xe (`ACTIVE`, `MAINTENANCE`, `INACTIVE`) và tài xế (`ACTIVE`, `INACTIVE`) được kiểm soát chặt chẽ. Cấm xóa cứng xe/tài xế đã có lịch sử booking (`soft-delete` only). | **PASS** |
| **III. Strict Concurrency & ACID** | Mọi thao tác đổi trạng thái và kiểm tra booking tương lai thực hiện trong một Transaction nguyên tử (`session.begin()`). | **PASS** |
| **IV. Test-Driven Verification (TDD)** | Kế hoạch kiểm thử tự động với `pytest` bao phủ 100% các Acceptance Scenarios (chuẩn hóa biển số, tải trọng <= 0, chặn xóa cứng, chặn đổi trạng thái khi kẹt lịch). | **PASS** |
| **V. Security & Observability** | Sử dụng Python standard `logging.getLogger(__name__)`. Masking exception thô trước khi gửi ra client. Xác thực dựa trên Session. | **PASS** |

## Project Structure

### Documentation (this feature)

```text
specs/001-truck-and-driver-management/
├── plan.md              # Kế hoạch triển khai kỹ thuật
├── research.md          # Kết quả nghiên cứu và quyết định kỹ thuật (Phase 0)
├── data-model.md        # Đặc tả Schema, Constraints, State transitions (Phase 1)
├── quickstart.md        # Hướng dẫn chạy và kịch bản nghiệm thu (Phase 1)
├── contracts/           # API Contracts OpenAPI 3.0 (Phase 1)
│   ├── trucks-api.yaml
│   └── drivers-api.yaml
└── tasks.md             # Danh sách atomic tasks (/speckit-tasks output - Phase 2)
```

### Source Code (repository root)

```text
src/
├── core/
│   ├── config.py           # Thiết lập môi trường & cấu hình ứng dụng
│   ├── database.py         # SQLAlchemy engine, session maker, base model
│   ├── exceptions.py       # Domain exceptions & centralized handlers
│   └── logging.py          # Cấu hình logging chuẩn
├── models/
│   ├── __init__.py
│   ├── truck.py            # SQLAlchemy Model: Truck, TruckStatus Enum
│   ├── driver.py           # SQLAlchemy Model: Driver, DriverStatus Enum
│   └── booking.py          # SQLAlchemy Model: ResourceBooking, BookingStatus Enum
├── schemas/
│   ├── __init__.py
│   ├── common.py           # ApiResponse generic envelope
│   ├── truck.py            # Pydantic v2 schemas: CreateTruck, UpdateTruck, TruckResponse
│   └── driver.py           # Pydantic v2 schemas: CreateDriver, UpdateDriver, DriverResponse
├── repositories/
│   ├── base.py             # Base repository pattern
│   ├── truck_repo.py       # Truy vấn Truck (normalized plate lookup, filter)
│   ├── driver_repo.py      # Truy vấn Driver (driver_code lookup, filter)
│   └── booking_repo.py     # Truy vấn ResourceBooking (xung đột lịch & lịch sử)
├── services/
│   ├── truck_service.py    # Nghiệp vụ xe: Chuẩn hóa biển số, validate tải trọng, guard trạng thái
│   └── driver_service.py   # Nghiệp vụ tài xế: Kiểm tra mã trùng, validate phone, guard trạng thái
├── api/
│   └── v1/
│       ├── __init__.py
│       ├── api_router.py   # Ghép nối các routers v1
│       ├── trucks.py       # REST API endpoints cho xe
│       └── drivers.py      # REST API endpoints cho tài xế
├── web/
│   ├── __init__.py
│   ├── admin_trucks.py     # Endpoints trả giao diện Jinja2 cho xe (/admin/trucks)
│   └── admin_drivers.py    # Endpoints trả giao diện Jinja2 cho tài xế (/admin/drivers)
├── templates/
│   ├── base.html           # Layout chung Bootstrap 5
│   ├── trucks/             # Giao diện danh sách, tạo mới, sửa xe
│   └── drivers/            # Giao diện danh sách, tạo mới, sửa tài xế
└── main.py                 # FastAPI application factory & lifespan

tests/
├── conftest.py             # Fixtures: in-memory DB session, test client, sample data
├── unit/
│   ├── test_trucks.py      # Test chuẩn hóa biển số, validate tải trọng, kiểm tra mã
│   └── test_drivers.py     # Test validate driver code, phone format
└── integration/
    ├── test_truck_lifecycle.py   # Test chuyển trạng thái xe & chặn khi vướng lịch
    └── test_soft_delete_guard.py # Test cấm xóa cứng khi có lịch sử booking
```

**Structure Decision**: Áp dụng cấu trúc phân tầng sạch chuẩn theo mô hình Web Application & REST API của FastAPI. Tách biệt hoàn toàn các tầng Router, Service, Repository, Model, đảm bảo khả năng kiểm thử độc lập cao.

## Complexity Tracking

Không có vi phạm nguyên tắc Hiến pháp nào cần giải trình (*Zero Constitutional Violations*).
