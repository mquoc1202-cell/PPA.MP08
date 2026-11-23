# Freight Transportation Management System v2.1

## TL;DR (Đọc trước — 60 giây)

> Đây là hệ thống **Quản lý Vận tải Hàng hóa (Freight Transportation Management)**.
> Nghiệp vụ gốc: `03_Freight_Transportation.pdf` (TRN-01 đến TRN-05, BR-06 đến BR-09, BR-15 đến BR-17).
> Backend: **Python 3.11+ (FastAPI)** + **SQLite**.
> Frontend: **Jinja2 Templates + Bootstrap 5**
> ORM & DB Access: **SQLAlchemy Core/ORM** với cơ chế Row-level Locking chống race condition.
> Architecture: **Layered Architecture (Router ➔ Service ➔ Repository ➔ DB)**.
> Hiến pháp dự án: Bắt buộc tuân thủ [`.specify/memory/constitution.md`](../.specify/memory/constitution.md).

---

## KIẾN TRÚC HỆ THỐNG

### Các Module / Router chính:

| Module / Service | URL Prefix | Mô tả nghiệp vụ | File / Package |
|---|---|---|---|
| **Auth & Users** | `/login`, `/logout`, `/admin/users` | Đăng nhập session, phân quyền vai trò (`DSP`, `SAL`, `MGR`) | `app/routers/auth.py` |
| **Trucks (TRN-01)** | `/trucks` | Quản lý đội xe: biển số, loại, tải trọng, trạng thái `ACTIVE/MAINTENANCE/INACTIVE` | `app/routers/trucks.py` |
| **Drivers (TRN-01)** | `/drivers` | Quản lý tài xế: mã, tên, SĐT, trạng thái `ACTIVE/INACTIVE` | `app/routers/drivers.py` |
| **Trips (TRN-02, 03, 04)** | `/trips` | Điều phối chuyến, chuyển đổi trạng thái (`UNASSIGNED` ➔ `ASSIGNED` ➔ `PICKED_UP` ➔ `IN_TRANSIT` ➔ `DELIVERED` ➔ `COMPLETED`) | `app/routers/trips.py` |
| **Schedules / Calendar** | `/schedules` | Lịch rảnh/bận của xe và tài xế (tính từ booking thực tế, không nhập tay) | `app/routers/schedules.py` |
| **Issues (TRN-05)** | `/issues` | Quản lý sự cố kỹ thuật, chậm tiến độ, cờ quá hạn vận hành | `app/routers/issues.py` |

### Flow xử lý chuyến hàng (Order & Trip Lifecycle):

```text
Đơn hàng xác nhận (UNASSIGNED)
       │
       ▼ (Điều phối viên DSP gán xe & tài xế hợp lệ: check tải trọng + không trùng lịch)
Đã phân công (ASSIGNED) ──[Tạo booking xe & tài xế]
       │
       ▼ (Ghi nhận nhận hàng thực tế, kiểm tra tải trọng thực tế, không vượt tải)
Đã nhận hàng (PICKED_UP) ──[Đơn sang IN_PROGRESS]
       │
       ▼ (Bắt đầu di chuyển)
Đang vận chuyển (IN_TRANSIT)
       │
       ▼ (Giao hàng: ghi nhận thời gian, người nhận, upload file bằng chứng PDF/JPG/PNG)
Đã giao hàng (DELIVERED)
       │
       ▼ (Kiểm tra đủ bằng chứng + không còn phụ phí PENDING)
Hoàn tất (COMPLETED) ──[Giải phóng lịch xe & tài xế]
```

---

## QUYẾT ĐỊNH KIẾN TRÚC QUAN TRỌNG (ADR)

### ADR-001: Dùng Transaction Locking (ACID) chống Race Condition trong Điều phối
* **Ngữ cảnh (TRN-02):** Hai điều phối viên (DSP) có thể cùng lúc chọn gán một xe hoặc tài xế cho hai chuyến có thời gian chồng chéo.
* **Quyết định:** Sử dụng Transaction với cơ chế khóa (`with_for_update()` trong SQLAlchemy hoặc `SERIALIZABLE` isolation level).
* **Kết quả:** Thao tác đầu tiên thành công và tạo booking; thao tác thứ hai bị rollback và nhận thông báo lỗi lịch đã bị chiếm dụng. Tuyệt đối không tạo booking một phần.

### ADR-002: State Machine độc lập & Bất biến (Immutable Audit Trail)
* **Ngữ cảnh (TRN-03, TRN-04):** Không được nhảy cóc trạng thái (ví dụ cấm chuyển `UNASSIGNED` sang thẳng `DELIVERED`), không xóa lịch sử giao dịch.
* **Quyết định:** Mọi thay đổi trạng thái đều đi qua `TripService.transition_state()` để kiểm tra điều kiện tiên quyết (Pre-conditions).
* **Soft Delete:** Xe và tài xế đã phát sinh giao dịch chỉ được chuyển sang `INACTIVE`, không bao giờ được `DELETE` cứng khỏi cơ sở dữ liệu.

### ADR-003: Repository Pattern & Tách biệt ORM
* **Ngữ cảnh:** Giữ tính độc lập, dễ test (`pytest`) và khả năng chuyển đổi DB từ SQLite sang PostgreSQL / SQL Server 2022.
* **Quyết định:** Toàn bộ truy vấn DB đóng gói trong `app/repositories/*_repository.py`. Tầng Service không viết truy vấn SQL trực tiếp.

---

## PATTERNS ĐƯỢC SỬ DỤNG

### 1. Repository Pattern:
* Tất cả truy vấn DB đi qua `app/repositories/*_repository.py`.
* Service layer chỉ gọi hàm Repository (ví dụ: `truck_repo.get_available_trucks()`), không viết câu lệnh query trực tiếp.

### 2. Error Handling & Logging:
* TUYỆT ĐỐI KHÔNG dùng `print()` trong mã nguồn. Bắt buộc dùng `logging.getLogger(__name__)`.
* Bắt ngoại lệ tập trung, ghi log stack trace nội bộ nhưng trả về thông báo lỗi thân thiện ra UI/API. Không để lộ exception thô ra client.

### 3. Session-Based Authentication:
* Dùng Session-based Cookie (HTTP-Only, Secure). Cấm dùng JWT khi chưa có yêu cầu đồng thuận.
* Bảo vệ router bằng Dependency Injection (`Depends(get_current_user)`, `Depends(require_role(["DSP", "MGR"]))`).

---

## NHỮNG GÌ ĐÃ KHÔNG HOẠT ĐỘNG (Lessons Learned)

- **[Khóa nguồn lực]:** Không kiểm tra xung đột lịch ở tầng frontend/client ➔ Dễ dẫn đến double-booking khi 2 người bấm cùng lúc. Phải khóa và kiểm tra ở tầng Database Transaction.
- **[Xóa dữ liệu]:** Tuyệt đối không hỗ trợ thao tác hard-delete cho xe và tài xế đã có lịch sử giao dịch để bảo toàn tính toàn vẹn báo cáo và lịch sử cuốc xe.
- **[Bằng chứng giao hàng (POD)]:** Bằng chứng bàn giao/giao hàng phải lưu file thật (PDF/JPG/PNG) và ghi nhận thời điểm thực tế, không tự động sinh hay giả lập thời gian từ hệ thống.

---

## FILE STRUCTURE QUAN TRỌNG

```text
/app
  /core            # config.py, database.py, security.py (session, password hashing)
  /models          # SQLAlchemy database models (Truck, Driver, Trip, Booking, Issue, Evidence)
  /schemas         # Pydantic v2 schemas (validation request/response)
  /repositories    # Data access layer (DB queries, transaction locks)
  /services        # Business logic: State Machine, Booking check, Capacity validation
  /routers         # FastAPI routers & endpoints (HTML render & JSON APIs)
  /templates       # Jinja2 views (layout/, auth/, trips/, trucks/, issues/)
  /static          # css/, js/, images/, uploads/
  main.py          # Entry point FastAPI app
/tests
  /unit            # Test logic Service cô lập (test_overweight, test_state_machine)
  /integration     # Test Database transactions & API endpoints với TestClient
```
