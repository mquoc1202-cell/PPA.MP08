# Implementation Plan: 003-trip-dispatch-and-conflict-management

**Branch**: `003-trip-dispatch-and-conflict-management` | **Date**: 2026-11-23 | **Spec**: [spec.md](file:///d:/PPA.MP08_GROUP3/specs/003-trip-dispatch-and-conflict-management/spec.md)  
**Input**: Feature specification from `specs/003-trip-dispatch-and-conflict-management/spec.md` (TRN-02)  

---

## Summary

Phân hệ **TRN-02: Điều phối chuyến hàng và quản lý trùng lịch** chịu trách nhiệm tiếp nhận các đơn hàng vận tải ở trạng thái `UNASSIGNED`, thực hiện gán xe tải và tài xế phù hợp theo tải trọng (`capacity_kg >= cargo_weight_kg`) và khung thời gian dự kiến `[start_time, end_time]`. Hệ thống kiểm soát tính nguyên tử (Atomic Transaction), ngăn chặn tuyệt đối xung đột trùng lịch (BR-07, BR-08) và tình trạng tranh chấp tài nguyên đồng thời giữa nhiều điều phối viên (Concurrency Lock). Phân hệ hỗ trợ đổi hoặc hủy phân công trước mốc nhận hàng (`PICKED_UP`), đồng thời cung cấp giao diện tra cứu lịch trình chiếm dụng nguồn lực trực quan.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI >= 0.110.0, SQLAlchemy >= 2.0.0, Pydantic v2 >= 2.6.0, Jinja2 >= 3.1.3, Bootstrap 5.3 + Bootstrap Icons 1.11, bcrypt >= 5.0.0  
**Storage**: SQLite (`freight_dev.db` cho môi trường cục bộ) / Tương thích PostgreSQL & SQL Server  
**Testing**: `pytest` + `pytest-asyncio` + `httpx` (TestClient)  
**Target Platform**: Web Server (Uvicorn) / SSR HTML + REST API  
**Project Type**: Phân tầng chuẩn doanh nghiệp (Layered Architecture: Router ➔ Service ➔ Repository ➔ Database)  
**Performance Goals**: Thời gian phản hồi điều phối < 200ms; phát hiện xung đột lịch tức thì (< 50ms)  
**Constraints**: 
- Tuân thủ nghiêm ngặt Hiến pháp dự án (`.specify/memory/constitution.md`) và quy chuẩn `AGENTS.md`.
- Tuyệt đối KHÔNG tạo booking một phần khi có lỗi (0% partial booking).
- Khóa chặt không cho đổi phân công khi chuyến đã sang `PICKED_UP`.
- Ghi log tập trung bằng thư viện chuẩn `logging` (nghiêm cấm `print()`).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Nguyên tắc Hiến pháp | Yêu cầu | Đánh giá Thiết kế TRN-02 | Trạng thái |
| :--- | :--- | :--- | :---: |
| **I. Layered Architecture** | Tách biệt Router ➔ Service ➔ Repository ➔ DB | `trips.py` (Router) chỉ nhận request/render; `dispatch_service.py` (Service) xử lý 100% logic tải trọng và trùng lịch; `trip_repo.py` & `booking_repo.py` (Repository) thực hiện truy vấn DB. | **PASSED** |
| **II. State Machine Integrity** | Chuyển trạng thái chuẩn xác, không nhảy cóc; bảo toàn lịch sử | Chuyến bắt đầu từ `UNASSIGNED` ➔ `ASSIGNED`. Chỉ được đổi/hủy phân công khi ở `ASSIGNED`. Khi đã `PICKED_UP` trở đi, hệ thống khóa chặn 100%. | **PASSED** |
| **III. Strict Concurrency & ACID** | Khóa tranh chấp đồng thời, giao dịch nguyên tử | Bọc toàn bộ quy trình kiểm tra + tạo booking trong 1 transaction; khóa xung đột giữa 2 điều phối viên; rollback toàn bộ nếu có lỗi. | **PASSED** |
| **IV. Test-Driven Verification (TDD)** | Bao phủ 100% kịch bản nghiệp vụ BR-06 đến BR-08 | Có test cases tự động cho: Quá tải trọng, Trùng lịch xe, Trùng lịch tài xế, Trùng lịch đồng thời (Race condition), Đổi phân công, và Khóa can thiệp sau `PICKED_UP`. | **PASSED** |
| **V. Security & Observability** | Xác thực tập trung, log chuẩn, cấm `print()` | Sử dụng Session cookie HTTP-Only; phân quyền `DSP` (ghi) vs `SAL`/`MGR` (chỉ đọc); ghi log qua `get_logger("dispatch")`. | **PASSED** |

---

## Project Structure

### Documentation (this feature)

```text
specs/003-trip-dispatch-and-conflict-management/
├── plan.md              # Kế hoạch triển khai kỹ thuật & kiến trúc
├── research.md          # Quyết định kỹ thuật: Locking, Overlap formula, State machine
├── data-model.md        # Mô hình thực thể Trip, ResourceBooking, Enums, Constraints
├── quickstart.md        # Hướng dẫn xác thực đầu cuối 4 kịch bản TRN-02
└── contracts/
    └── trips-api.yaml   # Hợp đồng REST API OpenAPI 3.0 cho Điều phối & Lịch trình
```

### Source Code Layout (repository root)

```text
src/
├── models/
│   ├── trip.py                 # SQLAlchemy model Trip (UNASSIGNED, ASSIGNED...)
│   └── booking.py              # ResourceBooking (bổ sung service_type: FREIGHT, RENTAL)
├── schemas/
│   ├── trip.py                 # Pydantic v2 schemas: CreateTripRequest, AssignTripRequest, ReassignTripRequest
│   └── schedule.py             # Pydantic v2 schemas cho tra cứu lịch trình
├── repositories/
│   ├── trip_repo.py            # TripRepository (filter, get_by_ref, update_status)
│   └── booking_repo.py         # ResourceBookingRepository (get_overlapping_bookings, cancel_bookings)
├── services/
│   └── dispatch_service.py     # DispatchService (validate tải trọng, lock & check trùng lịch, atomic booking)
├── api/v1/
│   ├── trips.py                # REST API endpoints (/api/v1/trips, /api/v1/trips/{id}/assign...)
│   └── schedule.py             # REST API endpoints tra cứu lịch trình (/api/v1/schedule/...)
├── web/
│   ├── trips.py                # SSR Web Controller (/trips, /trips/{id}/dispatch, /trips/{id})
│   └── schedule.py             # SSR Web Controller tra cứu lịch (/schedule)
└── templates/
    ├── trips/
    │   ├── list.html           # Danh sách chuyến hàng kèm bộ lọc trạng thái
    │   ├── dispatch.html       # Màn hình điều phối gán xe/tài xế & cảnh báo quá tải
    │   └── detail.html         # Chi tiết chuyến hàng và thông tin nguồn lực được gán
    └── schedule/
        └── index.html          # Màn hình danh sách lịch trình nguồn lực theo ngày/khoảng ngày

tests/
├── unit/
│   └── test_dispatch.py        # Kiểm thử unit: Quá tải, trùng lịch, atomic booking
├── integration/
│   └── test_dispatch_lifecycle.py # Kiểm thử vòng đời phân công, đổi phân công, concurrency lock
└── contract/
    └── test_trips_api.py       # Kiểm thử contract API tuân thủ contracts/trips-api.yaml
```

---

## Complexity Tracking

Không có vi phạm Hiến pháp nào cần giải trình (Zero Violations). Toàn bộ thiết kế bám sát kiến trúc phân tầng sẵn có của dự án.
