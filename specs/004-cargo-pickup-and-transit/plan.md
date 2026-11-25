# Implementation Plan: TRN-03 Ghi nhận nhận hàng và vận chuyển (Cargo Pickup & In-Transit Tracking)

**Branch**: `004-cargo-pickup-and-transit` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-cargo-pickup-and-transit/spec.md`

## Summary

Module TRN-03 hoàn thiện giai đoạn tiếp nhận hàng thực tế và bắt đầu vận chuyển trong chu trình đơn hàng:
- Chuyển trạng thái từ `ASSIGNED` ➔ `PICKED_UP` kèm ghi nhận thời điểm thực tế, người bàn giao, quy cách/tình trạng hàng và khối lượng cân thực tế.
- Kiểm tra tải trọng xe: tự động từ chối nếu khối lượng thực tế vượt tải trọng xe (`actual_cargo_weight_kg > truck.capacity_kg`), giữ nguyên `ASSIGNED` để điều phối xử lý lại nguồn lực.
- Kiểm tra xung đột thực thi theo quy tắc BR-09: ngăn chặn nhận hàng nếu xe hoặc tài xế đang thực hiện một chuyến khác (`IN_PROGRESS`).
- Chuyển trạng thái booking tài nguyên xe & tài xế từ `CONFIRMED` sang `IN_PROGRESS` khi nhận hàng thành công.
- Chuyển trạng thái từ `PICKED_UP` ➔ `IN_TRANSIT` khi xe xuất phát, chặn tuyệt đối mọi hành vi nhảy cóc trạng thái.
- Ghi nhận lịch sử dòng thời gian (Trip Events) lưu vết bất biến cả thời điểm thực tế và thời điểm ghi nhận hệ thống.

---

## Technical Context

**Language/Version**: Python 3.11+ (Python 3.13 compatible)  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.0+, Jinja2, Starlette Session Middleware  
**Storage**: SQLite (`freight_dev.db` cho dev/test) với kiến trúc sẵn sàng cho PostgreSQL / SQL Server 2022  
**Testing**: `pytest`, `pytest-asyncio`, `httpx` (FastAPI TestClient)  
**Target Platform**: Web Responsive (Desktop 1280px+ & Mobile/Tablet), Jinja2 SSR + Bootstrap 5 + Bootstrap Icons 1.11+  
**Project Type**: Layered Web Application + RESTful API  
**Performance Goals**: Thời gian phản hồi API chuyển trạng thái < 100ms; xử lý giao dịch nguyên tử (ACID transaction)  
**Constraints**:
- Tuân thủ nghiêm ngặt Hiến pháp dự án [constitution.md](../../.specify/memory/constitution.md)
- Không dùng `print()` — bắt buộc dùng Python standard `logging`
- Không nhảy cóc trạng thái: `ASSIGNED` ➔ `PICKED_UP` ➔ `IN_TRANSIT`
- Bất biến: Không sửa/xóa các mốc lịch sử đã xác nhận
- Phân quyền (RBAC): Chỉ `DSP` có quyền ghi; `SAL` và `MGR` chỉ có quyền đọc (403 Forbidden nếu ghi)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Constitutional Principle | Requirement in TRN-03 | Compliance Strategy | Status |
| :--- | :--- | :--- | :---: |
| **I. Layered Architecture** | Không đưa logic máy trạng thái vào Router/Template | Router gọi `TripTrackingService`, Service gọi `TripRepository` và `TripEventRepository` | ✅ PASS |
| **II. State Machine & Audit Trail** | Không nhảy cóc trạng thái (`ASSIGNED` ➔ `PICKED_UP` ➔ `IN_TRANSIT`). Lưu vết mốc bất biến. | Service validate trạng thái hiện tại. Tạo bản ghi `TripEvent` bất biến lưu thời điểm thực tế và thời điểm nhập. | ✅ PASS |
| **III. Strict Concurrency & ACID** | Cập nhật đồng bộ Trip và chuyển Booking sang `IN_PROGRESS` | Thực hiện trong một Transaction nguyên tử (`db.begin()`). Rollback nếu có lỗi. | ✅ PASS |
| **IV. Test-Driven Verification** | Kiểm thử tự động 100% các quy tắc BR-06, BR-09, State guard | Viết Unit tests, Contract tests và Integration tests trước khi nghiệm thu. | ✅ PASS |
| **V. Security & Observability** | Session cookie auth, logging chuẩn, RBAC | Kiểm tra quyền `require_role(["DSP"])` tại Router/Service, ghi log với `logger`. | ✅ PASS |

---

## Project Structure

### Documentation (this feature)

```text
specs/004-cargo-pickup-and-transit/
├── plan.md              # Kế hoạch kiến trúc (File hiện tại)
├── research.md          # Quyết định kỹ thuật & thiết kế máy trạng thái
├── data-model.md        # Thiết kế mở rộng Trip & bảng TripEvent
├── quickstart.md        # Hướng dẫn chạy & kiểm thử nghiệm thu
├── contracts/           # Hợp đồng giao tiếp API
│   └── pickup-api.yaml  # OpenAPI 3.0 spec cho Pickup & Transit endpoints
└── checklists/
    └── requirements.md  # Checklist thẩm định chất lượng đặc tả
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── trip.py                 # Mở rộng model Trip với các cột mốc thực tế
│   └── trip_event.py           # Model mới TripEvent lưu vết dòng thời gian
├── schemas/
│   └── trip.py                 # Mở rộng schemas: RecordPickupRequest, RecordDepartureRequest, TripEventItem
├── repositories/
│   ├── trip_repo.py            # Cập nhật TripRepository hỗ trợ cập nhật mốc
│   ├── trip_event_repo.py      # Repository quản lý dòng thời gian TripEvent
│   └── booking_repo.py         # Cập nhật chuyển trạng thái booking sang IN_PROGRESS
├── services/
│   └── trip_tracking_service.py # Xử lý nghiệp vụ nhận hàng, kiểm tra quá tải, BR-09 và khởi hành
├── api/v1/
│   └── trips.py                # Thêm endpoint POST /trips/{id}/pickup, POST /trips/{id}/depart, GET /trips/{id}/events
├── web/
│   └── trips.py                # Thêm controller GET /trips/{id}/pickup, POST /trips/{id}/pickup, POST /trips/{id}/depart
├── templates/
│   └── trips/
│       ├── detail.html         # Giao diện chi tiết chuyến hàng tích hợp dòng thời gian Timeline
│       ├── pickup.html         # Màn hình ghi nhận nhận hàng với cảnh báo tải trọng thực tế
│       └── list.html           # Cập nhật danh sách hiển thị các nút thao tác theo trạng thái mới
└── core/
    └── seed.py                 # Bổ sung dữ liệu mẫu cho các chuyến PICKED_UP và IN_TRANSIT
tests/
├── unit/
│   └── test_pickup.py          # Unit test nghiệp vụ nhận hàng, quá tải, BR-09, khởi hành
├── contract/
│   └── test_pickup_api.py      # Contract test OpenAPI endpoints
└── integration/
    └── test_trip_transitions.py # Integration test vòng đời chuyển trạng thái liên tục
```

---

## Complexity Tracking

Không có vi phạm hiến pháp cần miễn trừ. Mọi thành phần đều tuân thủ kiến trúc phân tầng chuẩn.
