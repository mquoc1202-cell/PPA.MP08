# Implementation Plan: TRN-05 Quản lý sự cố và chậm tiến độ (Incident & Delay Management)

**Branch**: `006-incident-and-delay-management` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-incident-and-delay-management/spec.md`

---

## Summary

Phân hệ **TRN-05: Quản lý sự cố và chậm tiến độ** chịu trách nhiệm cung cấp công cụ toàn diện cho Điều phối viên (`DSP`) nhằm:
1. Lập biên bản và giải quyết các sự cố phát sinh trong hành trình vận chuyển hàng hóa (`TripIssue`: `OPEN` ➔ `RESOLVED`).
2. Tự động phát hiện và cảnh báo cờ "Quá hạn vận hành" (`is_delayed`) khi `current_time > estimated_end_time` đối với các chuyến hàng chưa kết thúc.
3. Điều chỉnh lùi mốc thời gian kết thúc dự kiến (`estimated_end_time`), đồng thời tự động quét và cảnh báo các xung đột lịch trình kế tiếp của Xe tải và Tài xế mà không làm gián đoạn chuyến hiện tại; duy trì quy tắc **BR-09** (nguồn lực đang bận không được nhận việc mới).
4. Lưu vết kiểm toán bất biến trên Dòng thời gian (`TripEvent`: `ISSUE_LOGGED`, `ISSUE_RESOLVED`, `SCHEDULE_DELAYED`) và bảo vệ phân quyền nghiêm ngặt (chỉ `DSP` được thao tác ghi, `SAL`/`MGR` chỉ có quyền xem theo chuẩn HTTP 403 Forbidden). Tuyệt đối không tự suy diễn GPS, không tự động đổi trạng thái đơn và không tự đổi giá cước (tuân thủ **SAL-08**).

---

## Technical Context

**Language/Version**: Python 3.11+ (Python 3.13 tương thích)  
**Primary Dependencies**: FastAPI 0.115+, SQLAlchemy 2.0+, Pydantic v2, Jinja2, Starlette session, Bootstrap 5 + Bootstrap Icons 1.11  
**Storage**: SQLite (`freight_dev.db`) với Transaction Atomicity & Row Locking  
**Testing**: pytest 9.1+, pytest-asyncio, httpx (`TestClient`)  
**Target Platform**: Web Browser (Desktop Dispatcher $\ge$ 1280px, Responsive Tablet/Mobile)  
**Project Type**: Full-Stack Web Application (Layered Architecture: API + SSR Jinja2 Web)  
**Performance Goals**:
- Truy vấn danh sách sự cố và tính toán cờ quá hạn dynamically: $< 100\text{ ms}$.
- Quét và phát hiện xung đột lịch tương lai khi gia hạn: $< 500\text{ ms}$.  
**Constraints**:
- Tuân thủ 100% Hiến pháp dự án tại [.specify/memory/constitution.md](../../.specify/memory/constitution.md) và [AGENTS.md](../../AGENTS.md).
- Kiến trúc phân tầng tuyệt đối: Router ➔ Service ➔ Repository ➔ Database (SQLAlchemy).
- Không gọi SQL hoặc viết business logic trong template Jinja2 hay Router.
- Không dùng `print()`; bắt buộc dùng chuẩn Python `logging`.
- Session-based Cookie Authentication (HTTP-Only, Secure, SameSite).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc Hiến pháp | Yêu cầu Hiến pháp | Đánh giá thiết kế phân hệ TRN-05 | Trạng thái |
| :--- | :--- | :--- | :---: |
| **I. Layered Architecture** | Tách bạch Presentation, Service, Repository, Model | Presentation (`src/api/v1/`, `src/web/`) chỉ validate và render; Service (`IncidentService`) xử lý 100% logic sự cố & xung đột; Repository (`TripIssueRepository`, `ResourceBookingRepository`) thực hiện truy vấn DB. | **PASSED** |
| **II. State Machine & Audit Trail** | Không nhảy cóc trạng thái; bất biến lịch sử | Sự cố không tự động chuyển trạng thái chuyến sang `COMPLETED`; Dòng thời gian ghi nhận bất biến các mốc `ISSUE_LOGGED`, `ISSUE_RESOLVED`, `SCHEDULE_DELAYED`. | **PASSED** |
| **III. Strict Concurrency & ACID** | Khóa lịch trình chống race condition | Cập nhật gia hạn lịch trình được thực hiện trong Atomic Transaction với kiểm tra chồng lấn booking chéo giữa vận tải và cho thuê xe. | **PASSED** |
| **IV. Test-Driven Verification (TDD)** | Kiểm thử tự động 100% các kịch bản | Xây dựng đầy đủ unit tests, contract tests và integration tests bao phủ lập sự cố, đóng sự cố, phát hiện quá hạn, cảnh báo xung đột lịch tương lai và phân quyền RBAC. | **PASSED** |
| **V. Security & Observability** | Không lộ secret, dùng logging chuẩn, phân quyền vai trò | Xác thực cookie session an toàn; phân quyền `DSP` (ghi) vs `SAL`/`MGR` (xem); xử lý exception tập trung, ghi log an toàn. | **PASSED** |

---

## Project Structure

### Documentation (this feature)

```text
specs/006-incident-and-delay-management/
├── plan.md              # Kế hoạch kiến trúc kỹ thuật (Tệp này)
├── research.md          # Nghiên cứu giải pháp & quyết định kỹ thuật
├── data-model.md        # Mô hình dữ liệu, ERD và ràng buộc nghiệp vụ
├── quickstart.md        # Hướng dẫn xác thực và chạy kịch bản kiểm thử
├── contracts/           # Đặc tả giao diện OpenAPI 3.0
│   └── incident-api.yaml
└── checklists/          # Bảng kiểm tra chất lượng đặc tả
    └── requirements.md
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── trip_issue.py         # Mở rộng model TripIssue (occurred_at, handled_by, resolution_notes, resolved_at)
│   ├── trip_event.py         # Mở rộng TripEventType (ISSUE_LOGGED, ISSUE_RESOLVED, SCHEDULE_DELAYED)
│   └── trip.py               # Thuộc tính động is_delayed, has_open_issues
├── schemas/
│   └── trip.py               # Pydantic schemas (CreateTripIssueRequest, ResolveTripIssueRequest, RescheduleTripRequest)
├── repositories/
│   ├── trip_issue_repo.py    # TripIssueRepository (create, resolve, get_by_trip, get_open_issues_count)
│   ├── booking_repo.py       # Quét xung đột tương lai khi gia hạn: find_future_conflicts_for_resources
│   └── trip_repo.py          # Bộ lọc filter_trips bổ sung has_issues, is_delayed
├── services/
│   └── incident_service.py   # IncidentService: log_issue, resolve_issue, reschedule_trip_with_conflicts
├── api/v1/
│   └── trips.py              # REST endpoints (/issues, /issues/{id}/resolve, /reschedule)
├── web/
│   └── trips.py              # Web actions render modal, form submit và conflict alert
└── templates/
    └── trips/
        ├── detail.html       # Bổ sung nút Báo Cáo Sự Cố, Đóng Sự Cố, Gia Hạn Lịch, Modal Xung Đột
        └── list.html         # Bổ sung tab bộ lọc "Có Sự Cố", "Quá Hạn Vận Hành" và badge cảnh báo

tests/
├── unit/
│   ├── test_incidents.py     # Unit test lập/đóng sự cố, validation
│   └── test_reschedule.py    # Unit test gia hạn lịch, phát hiện xung đột lịch tương lai
├── contract/
│   └── test_incident_api.py  # Contract test REST API theo contracts/incident-api.yaml
└── integration/
    └── test_incident_lifecycle.py # Integration test toàn trình: Sự cố, Quá hạn, Xung đột tương lai, RBAC
```

---

## Complexity Tracking

*Không có vi phạm Hiến pháp nào cần giải trình.* Kiến trúc tuân thủ triệt để mô hình phân tầng đơn giản, trực quan và an toàn.
