# AGENTS.md

> **Phiên bản:** 2.0 (Python Edition)  
> **Cập nhật:** 2026-11  
> **Dự án:** Vận tải hàng hóa (Freight Transportation)

---

# 1. TỔNG QUAN DỰ ÁN & VAI TRÒ AI

## Thông tin dự án
* **Dự án:** Quản lý Vận tải Hàng hóa (Freight Transportation Management)
* **Tài liệu nghiệp vụ gốc:** `03_Freight_Transportation.pdf`
* **Hiến pháp dự án:** Bắt buộc tuân thủ toàn diện [`.specify/memory/constitution.md`](.specify/memory/constitution.md)

## Vai trò AI
Kỹ sư Full-Stack cấp Senior, chuyên sâu về Python (FastAPI / SQLAlchemy / Jinja2), kiến trúc phần mềm phân tầng (Layered Architecture / Clean Architecture) và kiểm thử tự động.

## Giới hạn phạm vi hoạt động (Non-negotiables)
* TUYỆT ĐỐI KHÔNG tự động thực thi `DROP TABLE`, `DELETE`, `TRUNCATE` trên database khi chưa có sự xác nhận rõ ràng.
* TUYỆT ĐỐI KHÔNG commit hoặc push trực tiếp lên nhánh `main` hoặc `master`.
* TUYỆT ĐỐI KHÔNG chỉnh sửa file `.env` hoặc nhúng secret/mật khẩu vào mã nguồn.

---

# 2. TECH STACK

> **BẮT BUỘC TUÂN THỦ — PHÙ HỢP NGHIỆP VỤ VẬN TẢI**

| Tầng          | Công nghệ                                                                            |
| ------------- | ------------------------------------------------------------------------------------ |
| Backend       | Python 3.11+ (FastAPI)                                                              |
| Frontend      | Jinja2 Templates + Bootstrap 5 |
| Cơ sở dữ liệu | SQLite |
| ORM / DB      | SQLAlchemy Core/ORM (hỗ trợ Transaction & Lock chống trùng lịch)                     |
| Validation    | Pydantic v2                                                                          |
| Xác thực      | Session-Based Cookie Authentication (HTTP-Only) + bcrypt                            |
| Test          | pytest + pytest-asyncio + httpx (TestClient)                                        |
| Server        | Uvicorn                                                                              |
| Tài liệu API  | OpenAPI 3.0 / Swagger UI tự động tại `/docs`                                         |

---

# 3. NGUYÊN TẮC KIẾN TRÚC & ĐIỀU HƯỚNG

## Quy tắc phân tầng

```text
Browser ➔ FastAPI Router ➔ Service Layer ➔ Repository Layer ➔ Database (SQLAlchemy)
Browser  Jinja2 / JSON  FastAPI Router  Service Layer  Repository Layer  Database
```

* **Router / Controller Layer (`app/routers/`):**
  * Nhận HTTP Request từ Browser/Client, trích xuất parameters.
  * Validate dữ liệu đầu vào qua Pydantic schemas.
  * Gọi Service layer tương ứng để thực hiện nghiệp vụ.
  * Trả về Jinja2 `TemplateResponse` (cho giao diện web) hoặc JSON response chuẩn (cho API).
  * TUYỆT ĐỐI KHÔNG viết logic nghiệp vụ hay câu truy vấn DB tại Router.

* **Service Layer (`app/services/`):**
  * Nơi xử lý 100% nghiệp vụ (Business Rules: BR-06 đến BR-09, BR-15 đến BR-17).
  * Kiểm soát chuyển đổi máy trạng thái (State Machine):
    `UNASSIGNED` ➔ `ASSIGNED` ➔ `PICKED_UP` ➔ `IN_TRANSIT` ➔ `DELIVERED` ➔ `COMPLETED`.
  * Kiểm tra điều kiện tải trọng, trùng lịch điều phối xe & tài xế.
  * Quản lý upload bằng chứng giao hàng (PDF/JPG/PNG).
  * TUYỆT ĐỐI KHÔNG nhận đối tượng HTTP request/response trực tiếp trong tầng Service.

* **Repository Layer (`app/repositories/`):**
  * Chứa toàn bộ thao tác truy vấn DB qua SQLAlchemy.
  * TUYỆT ĐỐI KHÔNG nối chuỗi SQL (phòng tránh SQL Injection).
  * BẮT BUỘC dùng cơ chế Transaction Atomicity và Khóa (Locking) khi thực hiện booking nguồn lực để chống race-condition giữa 2 điều phối viên.

* **Jinja2 Templates (`app/templates/`):**
  * Chỉ chịu trách nhiệm hiển thị giao diện.
  * TUYỆT ĐỐI KHÔNG viết logic nghiệp vụ tính toán trong template.
  * TUYỆT ĐỐI KHÔNG gọi Repository/DB trực tiếp từ template.

---

## URL Mapping

Các Router PHẢI đặt URL rõ ràng, RESTful, dễ hiểu:

```text
/login
/logout
/dashboard
/trucks, /trucks/create, /trucks/{id}/edit
/drivers, /drivers/create, /drivers/{id}/edit
/trips, /trips/{id}, /trips/dispatch
/issues, /issues/create, /issues/{id}
```

Với các chức năng quản trị hoặc theo vai trò:

```text
/admin/users
/admin/trucks
/admin/reports
```

Nếu có API trả JSON thì dùng pattern:

```text
/api/v1/{resource}
Ví dụ: /api/v1/trucks, /api/v1/trips/{id}/status
```

---

## Response

Với request hiển thị giao diện HTML (Jinja2):

```python
from fastapi.responses import HTMLResponse, RedirectResponse

# Render giao diện template
return templates.TemplateResponse(
    "trips/detail.html",
    {"request": request, "trip": trip, "current_user": user}
)

# Hoặc chuyển hướng (Redirect)
return RedirectResponse(url="/dashboard", status_code=303)
```

Với API trả JSON:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {}
}
```

Trong Python:
```python
from app.schemas.response import ApiResponse

return ApiResponse(success=True, data={"trip_id": trip.id}, meta={"total": 1})
```

---

## Xử lý lỗi & Logging

TẤT CẢ lỗi phải được xử lý tập trung, không hiển thị exception thô (stack trace) cho người dùng.

* TUYỆT ĐỐI KHÔNG dùng hàm `print()` để debug trong mã nguồn.
* BẮT BUỘC dùng chuẩn thư viện `logging` của Python:

```python
import logging

logger = logging.getLogger(__name__)
```

* TUYỆT ĐỐI KHÔNG trả message exception thô ra giao diện:

```python
# SAI: Để lộ exception thô
except Exception as e:
    return templates.TemplateResponse("error/500.html", {"request": request, "error": str(e)})

# ĐÚNG: Ghi log chi tiết nội bộ, trả thông báo an toàn ra giao diện
except Exception as e:
    logger.error("Error while processing trip assignment: %s", e, exc_info=True)
    return templates.TemplateResponse(
        "error/500.html",
        {"request": request, "error": "Có lỗi xảy ra trong quá trình xử lý, vui lòng thử lại sau."},
        status_code=500
    )
```

---

## Xác thực (Authentication)

* Dùng Session-Based Cookie Authentication (HTTP-Only, Secure, SameSite).
* TUYỆT ĐỐI KHÔNG dùng JWT nếu chưa được thống nhất.
* TUYỆT ĐỐI KHÔNG hardcode `user_id`.
* Sau khi đăng nhập: lưu thông tin user vào session an toàn.
  ```python
  request.session["current_user"] = {"id": user.id, "username": user.username, "role": user.role}
  ```
* Khi đăng xuất: xóa sạch session:
  ```python
  request.session.clear()
  ```
* Các trang cần đăng nhập đi qua Dependency / Middleware kiểm tra:
  ```python
  from fastapi import Depends
  from app.core.security import get_current_user

  @router.get("/dashboard")
  def dashboard_page(request: Request, current_user = Depends(get_current_user)):
      ...
  ```

---

## Phân quyền (Authorization)

* Kiểm tra quyền trong Dependency hoặc Service, không hardcode phân quyền logic rời rạc trong giao diện template.
* User chưa đăng nhập ➔ Redirect về `/login`.
* User không đủ quyền (ví dụ: SAL xem trái quyền thao tác của DSP) ➔ Trả mã HTTP 403 và render giao diện `templates/error/403.html`.
* Các vai trò chính theo tài liệu vận tải:
  * `DSP` (Điều phối viên): Thực hiện điều phối, gán xe/tài xế, cập nhật mốc nhận hàng, giao hàng, sự cố.
  * `SAL / MGR` (Kinh doanh / Quản lý): Xem theo quyền tra cứu, không có quyền điều phối hoặc đổi trạng thái.

---

## Cơ sở dữ liệu & Chống SQL Injection

* TẤT CẢ truy vấn database bắt buộc đi qua tầng Repository / DAO.
* TUYỆT ĐỐI KHÔNG viết câu lệnh SQL trong Router hoặc Service layer.
* TUYỆT ĐỐI KHÔNG nối chuỗi SQL dạng f-string (`f"SELECT * FROM trucks WHERE plate = '{plate}'"`).
* BẮT BUỘC dùng cơ chế Parameterized Query hoặc ORM (SQLAlchemy Query / Select statement):

```python
# ĐÚNG: Dùng SQLAlchemy ORM hoặc Parameterized Query
stmt = select(Truck).where(Truck.plate_number == normalized_plate)
result = db.execute(stmt).scalars().first()
```

---

## Transaction & Kiểm soát đồng thời (ACID & Concurrency)

Với các nghiệp vụ nhiều bước (đặc biệt là phân công xe/tài xế trong TRN-02):
* BẮT BUỘC dùng Transaction: commit khi mọi bước hợp lệ, rollback ngay khi có bất kỳ lỗi nào.
* BẮT BUỘC kiểm tra xung đột trùng lịch và khóa (Locking) để đảm bảo hai điều phối viên cùng gán 1 xe trong cùng thời điểm chỉ duy nhất 1 người thành công:

```python
try:
    with db.begin():
        # 1. Kiểm tra trạng thái chuyến, tải trọng, trùng lịch với lock
        dispatch_service.validate_and_lock_resources(db, trip_id, truck_id, driver_id, start_time, end_time)
        # 2. Cập nhật trạng thái chuyến sang ASSIGNED
        # 3. Tạo booking xe và tài xế
        # Transaction tự động commit nếu không có exception
except ScheduleConflictException as e:
    db.rollback()
    logger.warning("Schedule conflict detected for trip %s: %s", trip_id, e)
    raise ConflictError("Xe hoặc tài xế đã bị chiếm dụng trong khoảng thời gian này, vui lòng kiểm tra lại lịch.")
except Exception as e:
    db.rollback()
    logger.error("Failed to assign trip %s: %s", trip_id, e, exc_info=True)
    raise e
```

---

## Quy chuẩn phát triển Frontend (Jinja2 + Bootstrap 5 + Design System)

Toàn bộ giao diện người dùng (UI) PHẢI đồng bộ theo Design System được quy định tại `frontend/DESIGN.md` và tuân thủ các quy tắc sau:

### 1. Bảng màu & Visual Tokens chuẩn (Đồng bộ `frontend/DESIGN.md`)
* **Màu chủ đạo (Brand Colors):**
  * Primary Corporate Blue: `#1c69d4` (Navbar, primary CTA buttons, important links).
  * Primary Active/Hover: `#0653b6`.
  * Dark Surface / Accent: `#1a2129` (Navy header bands, elevated containers).
* **Nền & Bề mặt (Canvas & Surfaces):**
  * Body Background: `#f8f9fa` (Canvas dịu mắt, tương phản tốt).
  * Card Surface: `#ffffff` với bo góc `border-radius: 8px`, bóng đổ nhẹ `box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.075)`.
* **Trạng thái & Badges hệ thống:**
  * `ACTIVE` / `COMPLETED` / `CONFIRMED`: Màu xanh lá `#22c55e` (`badge bg-success`).
  * `MAINTENANCE` / `PENDING` / `ASSIGNED`: Màu vàng cam `#f59e0b` (`badge bg-warning text-dark`).
  * `IN_PROGRESS` / `IN_TRANSIT` / `PICKED_UP`: Màu xanh dương `#1c69d4` (`badge bg-primary`).
  * `INACTIVE` / `CANCELLED`: Màu xám `#6c757d` (`badge bg-secondary`).
  * `OVERWEIGHT` / `DELAYED` / `ISSUE`: Màu đỏ `#dc2626` (`badge bg-danger`).
* **Icon set:** BẮT BUỘC dùng **Bootstrap Icons 1.11+** (`<i class="bi bi-..."></i>`), không dùng icon rời rạc hay emoji tự do.

### 2. Cấu trúc Kế thừa Template Jinja2 (Layout Hierarchy)
* Mọi trang giao diện BẮT BUỘC kế thừa từ `templates/base.html`:
  ```jinja2
  {% extends "base.html" %}
  {% block title %}Tiêu đề trang - Freight ERP{% endblock %}
  {% block content %}
    <!-- Nội dung chính -->
  {% endblock %}
  {% block extra_scripts %}
    <!-- Script riêng nếu có -->
  {% endblock %}
  ```
* `templates/base.html` chứa:
  * Top Navigation Bar cố định hiển thị Logo, điều hướng các phân hệ (`Đội Xe`, `Tài Xế`, `Chuyến Hàng`, `Sự Cố`), Badge hiển thị vai trò (`DSP`, `SAL`, `MGR`), và nút xem OpenAPI Docs.
  * Vùng hiển thị thông báo flash message tự động (`error_message`, `success_message`).
  * Responsive layout chuẩn cho màn hình điều phối Desktop (tối thiểu 1280px) và Mobile/Tablet.

### 3. Quy chuẩn Form & Tương tác Dữ liệu (Forms & User Inputs)
* Các trường bắt buộc nhập PHẢI có dấu hoa thị đỏ: `<span class="text-danger">*</span>`.
* Dưới mỗi input quan trọng PHẢI có dòng hướng dẫn định dạng (`<div class="form-text text-muted">...</div>`).
* **Khi Submit Form:**
  * Thành công: Chuyển hướng với HTTP 303: `RedirectResponse(url="/admin/resource?success=true", status_code=303)`.
  * Lỗi nghiệp vụ hoặc dữ liệu không hợp lệ: Render lại form với HTTP status 400, hiển thị thông báo lỗi trong `<div class="alert alert-danger">` và GIỮ NGUYÊN các giá trị người dùng đã nhập trong form (không bắt người dùng nhập lại từ đầu).

### 4. Quy chuẩn Bảng Dữ liệu (Data Tables & Empty States)
* Bảng hiển thị thông tin phải có header `thead class="table-light"`.
* Cột ID/Mã định danh in đậm: `<td class="fw-bold">...</td>`.
* Cột trạng thái phải dùng Badge chuẩn (`badge bg-...`).
* Cột Thao tác căn lề phải (`text-end pe-3`) với nút kích thước nhỏ (`btn-sm`).
* **Empty State:** Khi không có dữ liệu hoặc không khớp bộ lọc, BẮT BUỘC hiển thị icon trống và thông báo rõ ràng:
  ```html
  <tr>
    <td colspan="N" class="text-center py-4 text-muted">
      <i class="bi bi-inbox fs-2 d-block mb-2"></i> Chưa có dữ liệu nào trong danh mục hoặc không khớp bộ lọc.
    </td>
  </tr>
  ```

### 5. Hộp thoại Cảnh báo & Modal Xung đột (Confirmation & Conflict Modals)
* **Xác nhận xóa/chuyển trạng thái nguy hiểm:** Phải có dialog xác nhận từ người dùng (`data-bs-toggle="modal"` hoặc confirm dialog).
* **Xung đột lịch trình (HTTP 409 Schedule Conflict):** Khi điều phối viên cố tình chuyển trạng thái xe/tài xế sang `MAINTENANCE` hoặc `INACTIVE` mà còn lịch tương lai, giao diện BẮT BUỘC mở Modal hoặc bảng cảnh báo liệt kê chi tiết: Mã đơn (`reference_code`), thời gian bắt đầu (`start_time`), thời gian kết thúc (`end_time`) bị xung đột.

### 6. Phân quyền hiển thị giao diện theo Vai trò (Role-Based UI Rendering)
* Mọi view PHẢI truyền `current_user` vào template context.
* Nút thao tác điều phối (Thêm, Sửa, Gán lịch, Đổi trạng thái) CHỈ hiển thị khi người dùng là `DSP`:
  ```jinja2
  {% if current_user.role == 'DSP' %}
    <a href="/admin/trucks/create" class="btn btn-primary">Thêm Xe Mới</a>
  {% endif %}
  ```
* Người dùng vai trò `SAL` hoặc `MGR` chỉ nhìn thấy dữ liệu ở chế độ Read-only.

---

# 4. CẤU TRÚC THƯ MỤC CHUẨN

```text
app/
├── core/              # config.py, database.py, security.py (session, hash, auth dependency)
├── models/            # SQLAlchemy database models (Truck, Driver, Trip, Booking, Issue, Evidence)
├── schemas/           # Pydantic schemas (Request / Response validation)
├── repositories/      # Data access layer (TruckRepository, DriverRepository, TripRepository, BookingRepository...)
├── services/          # Business logic & state machine (DispatchService, TripService, IssueService...)
├── routers/           # FastAPI endpoints (auth.py, trucks.py, drivers.py, trips.py, issues.py)
├── templates/         # Jinja2 views
│   ├── layout/        # base.html, header.html, sidebar.html, footer.html
│   ├── auth/          # login.html
│   ├── dashboard/     # index.html
│   ├── trucks/        # list.html, form.html, detail.html
│   ├── drivers/       # list.html, form.html, detail.html
│   ├── trips/         # list.html, dispatch.html, detail.html
│   └── error/         # 403.html, 404.html, 500.html
├── static/            # css/, js/, images/, uploads/
└── main.py            # FastAPI Application entrypoint
tests/
├── conftest.py        # Fixtures, test database setup (in-memory SQLite / test DB)
├── test_services/     # Unit test logic nghiệp vụ (overweight, conflict, state machine)
└── test_api/          # Integration test endpoints qua TestClient
```

---

# 5. CÁC MẪU BỊ CẤM

## Frontend / Jinja2
* TUYỆT ĐỐI KHÔNG đưa nghiệp vụ tính toán hoặc kiểm tra trạng thái phức tạp vào file template Jinja2.
* TUYỆT ĐỐI KHÔNG gọi trực tiếp database hoặc service từ trong file template.

## Backend / Python
* TUYỆT ĐỐI KHÔNG dùng hàm `print()` — BẮT BUỘC dùng Python standard `logging`.
* TUYỆT ĐỐI KHÔNG đặt logic nghiệp vụ trong Router.
* TUYỆT ĐỐI KHÔNG viết SQL trong Router hoặc Service.
* TUYỆT ĐỐI KHÔNG nhận đối tượng HTTP request trong Service.
* TUYỆT ĐỐI KHÔNG hardcode `user_id` hay role người dùng.

## Nghiệp vụ Vận tải (Business Guardrails)
* TUYỆT ĐỐI KHÔNG xóa cứng (hard delete) dữ liệu Xe hoặc Tài xế đã từng tham gia vận chuyển (chỉ chuyển trạng thái `INACTIVE` / soft-delete để bảo toàn lịch sử).
* TUYỆT ĐỐI KHÔNG cho phép chuyển trạng thái chuyến nhảy cóc (ví dụ: cấm nhảy từ `UNASSIGNED` sang `DELIVERED`).
* TUYỆT ĐỐI KHÔNG tạo booking một phần (nếu xe hoặc tài xế trùng lịch thì hủy toàn bộ booking).

## Xác thực & Bảo mật
* TUYỆT ĐỐI KHÔNG dùng JWT nếu chưa được thống nhất.
* TUYỆT ĐỐI KHÔNG lưu `password` bản rõ trong session hoặc database.
* TUYỆT ĐỐI KHÔNG hardcode DB credentials, secret key trong mã nguồn.
* TUYỆT ĐỐI KHÔNG ghi log các thông tin nhạy cảm.
* TUYỆT ĐỐI KHÔNG commit file `.env` hoặc file chứa secret lên Git.

---

# 6. ĐỊNH NGHĨA HOÀN THÀNH (DEFINITION OF DONE)

Trước khi nghiệm thu một tính năng:
- [ ] Chạy `pytest` thành công 100%, không có test case nào lỗi.
- [ ] Các kịch bản ràng buộc nghiệp vụ (BR-06 đến BR-09, BR-15 đến BR-17) đều có test case tự động bao phủ.
- [ ] Mã nguồn tuân thủ Hiến pháp tại `.specify/memory/constitution.md`.
- [ ] API có tài liệu hiển thị đầy đủ trên Swagger UI `/docs`.
- [ ] Không còn lệnh `print()` hoặc TODO dở dang.
