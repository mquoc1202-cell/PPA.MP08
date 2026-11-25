# Implementation Plan: TRN-04 Xác nhận giao hàng và hoàn tất (Delivery Confirmation & Trip Completion)

**Branch**: `005-delivery-and-completion` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-delivery-and-completion/spec.md`

## Summary

Module TRN-04 hiện thực hóa quy trình nghiệp vụ chặng cuối trong vòng đời vận tải:
1. Xác nhận giao hàng thực tế (`IN_TRANSIT` ➔ `DELIVERED`) kèm lưu trữ an toàn các tệp chứng từ bàn giao (Proof of Delivery - POD: PDF, JPG, PNG) và thông tin người nhận.
2. Xử lý ngoại lệ giao hàng không thành công (`FAILED`): giữ nguyên `IN_TRANSIT`, không chuyển `DELIVERED`, và lập biên bản sự cố (`TripIssue`).
3. Chốt hoàn tất chuyến hàng (`DELIVERED` ➔ `COMPLETED`): kiểm tra điều kiện đủ bằng chứng POD và không có phụ phí `PENDING`; lưu thời điểm giải phóng xe/tài xế thực tế; chuyển trạng thái `ResourceBooking` của Xe tải và Tài xế sang `COMPLETED`, giải phóng tài nguyên lập tức cho các chuyến kế tiếp theo quy tắc BR-09.
4. Quản lý, xem và tải tệp chứng từ POD, hiển thị dòng thời gian sự kiện (`TripEvent`) và nhật ký sự cố.
5. Kiểm soát phân quyền RBAC: chỉ vai trò `DSP` mới được quyền ghi/thao tác; vai trò `SAL` và `MGR` xem ở chế độ chỉ đọc (Read-only).

---

## Technical Context

**Language/Version**: Python 3.11+ (hiện hành: Python 3.13)  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy Core/ORM, Jinja2, Bootstrap 5, Bootstrap Icons 1.11, python-multipart (cho file upload)  
**Storage**: SQLite (`freight_dev.db`) cho môi trường phát triển & kiểm thử; hệ thống tệp cục bộ bảo mật (`src/static/uploads/evidence/`) lưu trữ tệp chứng từ POD  
**Testing**: `pytest`, `httpx` (FastAPI TestClient), `pytest-asyncio`  
**Target Platform**: Linux / Windows Server (FastAPI + Uvicorn)  
**Project Type**: Web Application kết hợp RESTful API v1 và Server-Side Rendering (Jinja2 Templates)  
**Performance Goals**: Thời gian phản hồi API < 200ms; xử lý tải tệp POD < 1s; giải phóng tài nguyên tức thời trong 1 database transaction  
**Constraints**: 
- Dung lượng mỗi tệp chứng từ POD $\le 10$ MB; định dạng hỗ trợ: PDF, JPG, JPEG, PNG
- Máy trạng thái nghiêm ngặt: `IN_TRANSIT` ➔ `DELIVERED` ➔ `COMPLETED` (không nhảy cóc trạng thái)
- Kiểm soát thời gian: `actual_delivery_time >= actual_pickup_time`, `actual_completed_time >= actual_delivery_time`, `actual_completed_time <= current_time`
- Phân quyền chặt chẽ: `DSP` có quyền ghi, `SAL`/`MGR` chỉ đọc (HTTP 403 Forbidden khi vi phạm)
- Không dùng `print()`, dùng chuẩn `logging` tập trung  
**Scale/Scope**: Quản lý toàn bộ vòng đời kết thúc đơn vận tải, tải chứng từ POD, nhật ký sự cố và giải phóng tài nguyên

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên Tắc Hiến Pháp | Yêu Cầu Cốt Lõi | Mức Độ Tuân Thủ Trong Kế Hoạch TRN-04 | Đánh Giá |
|----------------------|-----------------|----------------------------------------|----------|
| **I. Layered Architecture** | Router ➔ Service ➔ Repository ➔ DB. Router không chứa business logic/SQL; Service độc lập HTTP; Repository xử lý queries. | - Router: Nhận file multipart/form-data và JSON, gọi Service.<br>- Service: Xử lý quy tắc giao hàng, xác thực mốc thời gian, quản lý file, kiểm soát phụ phí và giải phóng booking.<br>- Repository: Thao tác bảng `trips`, `trip_evidence`, `trip_issues`, `resource_bookings`, `trip_events`. | **PASS** |
| **II. State Machine & Audit Trail** | Không nhảy cóc trạng thái: `IN_TRANSIT` ➔ `DELIVERED` ➔ `COMPLETED`. POD bắt buộc trước `DELIVERED`/`COMPLETED`. Lưu vết bất biến `TripEvent`. | - Kiểm tra trạng thái nguồn: chỉ `IN_TRANSIT` mới được giao hàng; chỉ `DELIVERED` mới được hoàn tất.<br>- Chặn hoàn tất nếu thiếu bằng chứng POD.<br>- Ghi nhận đầy đủ `TripEvent` với thời điểm thực tế và thời điểm hệ thống. | **PASS** |
| **III. Strict Concurrency & ACID** | Thao tác nhiều bước phải nằm trong Transaction: chuyển trạng thái đơn, giải phóng booking, ghi nhận sự kiện. | Dùng `with db.begin():` đảm bảo cập nhật trạng thái `Trip`, chuyển trạng thái `ResourceBooking` (Xe & Tài xế) sang `COMPLETED`, và ghi `TripEvent` hoàn tất trong 1 atomic transaction duy nhất. | **PASS** |
| **IV. Test-Driven Verification** | Kiểm thử tự động pytest bao phủ các kịch bản biên, lỗi thời gian, thiếu bằng chứng và phân quyền. | Xây dựng bộ test suite: unit tests (logic chuyển trạng thái, chặn thời gian sai), integration tests (vòng đời từ giao hàng đến hoàn tất, kiểm tra giải phóng BR-09, RBAC), contract tests (REST API). | **PASS** |
| **V. Security & Observability** | Xác thực session-based cookie, kiểm soát quyền theo vai trò (RBAC), dùng chuẩn `logging`, không dùng `print()`. | - Áp dụng `require_role(["DSP"])` cho các endpoint ghi nhận.<br>- Người dùng `SAL`/`MGR` bị chặn HTTP 403 khi thao tác ghi.<br>- Sử dụng logger `get_logger(__name__)`. | **PASS** |

---

## Project Structure

### Documentation (this feature)

```text
specs/005-delivery-and-completion/
├── spec.md              # Đặc tả nghiệp vụ gốc (User Stories & Requirements)
├── plan.md              # Kế hoạch triển khai kỹ thuật & kiến trúc phân tầng (File này)
├── research.md          # Kết quả nghiên cứu kỹ thuật & quyết định thiết kế (Phase 0)
├── data-model.md        # Thiết kế lược đồ dữ liệu, thực thể & máy trạng thái (Phase 1)
├── contracts/           # Hợp đồng giao tiếp API RESTful (Phase 1)
│   └── delivery-api.yaml
├── quickstart.md        # Hướng dẫn chạy & kiểm thử nghiệm thu tính năng (Phase 1)
├── checklists/          # Bảng kiểm định chất lượng đặc tả
│   └── requirements.md
└── tasks.md             # Danh sách đầu việc chi tiết (Phase 2 - sinh bởi /speckit-tasks)
```

### Source Code (repository layout)

```text
src/
├── models/
│   ├── trip.py                 # Mở rộng Trip với actual_delivery_time, recipient_name, actual_completed_time...
│   ├── trip_evidence.py        # Model mới: TripEvidence (quản lý tệp chứng từ POD)
│   ├── trip_issue.py           # Model mới: TripIssue (quản lý sự cố khi giao thất bại)
│   ├── trip_event.py           # Bổ sung TripEventType (DELIVERY_CONFIRMED, DELIVERY_FAILED, TRIP_COMPLETED)
│   ├── booking.py              # Đã có ResourceBooking & BookingStatus.COMPLETED
│   └── __init__.py             # Export các model mới
├── schemas/
│   └── trip.py                 # Pydantic schemas: RecordDeliveryRequest, CompleteTripRequest, TripEvidenceItem...
├── repositories/
│   ├── trip_repo.py            # Mở rộng truy vấn chuyến theo DELIVERED, COMPLETED
│   ├── trip_evidence_repo.py   # Repository mới: TripEvidenceRepository (lưu trữ & truy vấn chứng từ)
│   ├── trip_issue_repo.py      # Repository mới: TripIssueRepository (ghi nhận sự cố giao hàng)
│   ├── trip_event_repo.py      # Ghi nhận các sự kiện DELIVERY_CONFIRMED, TRIP_COMPLETED
│   └── booking_repo.py         # Chuyển booking sang COMPLETED và cập nhật end_time
├── services/
│   ├── delivery_service.py     # Service mới: DeliveryService (nghiệp vụ giao hàng, lưu file POD, hoàn tất, giải phóng tài nguyên)
│   └── trip_tracking_service.py# Tích hợp hoặc điều phối chung
├── api/v1/
│   └── trips.py                # REST API: POST /trips/{id}/deliver, POST /trips/{id}/complete, GET/POST evidence
├── web/
│   └── trips.py                # SSR Controller: GET/POST /trips/{id}/deliver, POST /trips/{id}/complete, download file
├── templates/
│   └── trips/
│       ├── deliver.html        # Màn hình ghi nhận giao hàng (form nhập người nhận, kết quả, kéo thả tệp POD)
│       ├── detail.html         # Cập nhật: danh sách chứng từ POD, sự cố, modal hoàn tất chuyến
│       └── list.html           # Cập nhật: tab DELIVERED, COMPLETED, nút thao tác theo trạng thái
├── static/
│   └── uploads/
│       └── evidence/           # Thư mục lưu trữ an toàn các tệp chứng từ POD được tải lên
tests/
├── unit/
│   └── test_delivery.py        # Unit tests cho DeliveryService (giao thành công, giao thất bại, thiếu POD, mốc thời gian sai, hoàn tất)
├── integration/
│   └── test_delivery_lifecycle.py # Integration tests: Vòng đời IN_TRANSIT -> DELIVERED -> COMPLETED, giải phóng BR-09, RBAC
└── contract/
    └── test_delivery_api.py    # Contract test kiểm tra các endpoint REST API delivery & completion
```

**Structure Decision**: Áp dụng kiến trúc phân tầng Layered Architecture hiện hữu của dự án (`Presentation` ➔ `Service` ➔ `Repository` ➔ `Database`), đồng bộ giữa REST API JSON và Web SSR Jinja2 Templates.

---

## Complexity Tracking

> Không có vi phạm Hiến pháp nào cần biện minh (Tất cả các nguyên tắc đều được tuân thủ nghiêm ngặt).
