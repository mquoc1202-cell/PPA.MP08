# Quickstart & Validation Guide: TRN-01 Quản lý xe và tài xế

Tài liệu hướng dẫn thiết lập môi trường, chạy kiểm thử tự động (`pytest`) và thực thi các kịch bản kiểm thử nghiệm thu (Acceptance Scenarios) của module TRN-01.

---

## 1. Môi trường yêu cầu (Prerequisites)

- Python 3.11+
- Virtualenv (`venv`)
- Các thư viện cốt lõi:
  ```text
  fastapi>=0.110.0
  uvicorn[standard]>=0.28.0
  pydantic>=2.6.0
  sqlalchemy>=2.0.28
  jinja2>=3.1.3
  pytest>=8.0.0
  httpx>=0.27.0
  ```

---

## 2. Cài đặt và Khởi chạy

### Bước 1: Kích hoạt môi trường ảo & cài đặt dependencies
```powershell
# Tạo và kích hoạt venv
python -m venv .venv
.venv\Scripts\activate

# Cài đặt thư viện
pip install -r requirements.txt
```

### Bước 2: Khởi động máy chủ FastAPI
```powershell
uvicorn src.main:app --reload --port 8000
```
- Swagger UI (OpenAPI Docs): [http://localhost:8000/docs](http://localhost:8000/docs)
- Giao diện quản lý xe: [http://localhost:8000/admin/trucks](http://localhost:8000/admin/trucks)
- Giao diện quản lý tài xế: [http://localhost:8000/admin/drivers](http://localhost:8000/admin/drivers)

---

## 3. Chạy Kiểm Thử Tự Động (Automated Verification)

Chạy toàn bộ bộ test cho TRN-01:
```powershell
pytest tests/unit/test_trucks.py tests/unit/test_drivers.py tests/integration/test_truck_lifecycle.py -v
```

Mục tiêu nghiệm thu: **100% tests PASS**.

---

## 4. Kịch bản xác minh thủ công / API Scenarios

### Kịch bản 1: Tạo xe thành công và chuẩn hóa biển số
- **Request**:
  ```bash
  curl -X POST http://localhost:8000/api/v1/trucks \
    -H "Content-Type: application/json" \
    -d '{
      "plate_number": "29C-123.45",
      "truck_type": "Xe thùng kín 5T",
      "capacity_kg": 5000,
      "description": "Xe chạy tuyến HN - HP"
    }'
  ```
- **Kỳ vọng**: HTTP 201 Created. `data.normalized_plate` tự động được tính là `"29C12345"`.

### Kịch bản 2: Từ chối biển số trùng lặp sau chuẩn hóa
- **Request**:
  ```bash
  curl -X POST http://localhost:8000/api/v1/trucks \
    -H "Content-Type: application/json" \
    -d '{
      "plate_number": "29c 123.45",
      "truck_type": "Xe bạt 5T",
      "capacity_kg": 5000
    }'
  ```
- **Kỳ vọng**: HTTP 409 Conflict. `error` thông báo biển số đã tồn tại.

### Kịch bản 3: Từ chối tải trọng <= 0
- **Request**:
  ```bash
  curl -X POST http://localhost:8000/api/v1/trucks \
    -H "Content-Type: application/json" \
    -d '{
      "plate_number": "30A-999.99",
      "truck_type": "Xe tải",
      "capacity_kg": 0
    }'
  ```
- **Kỳ vọng**: HTTP 400 Bad Request. `error` thông báo tải trọng phải lớn hơn 0 kg.

### Kịch bản 4: Chặn đổi sang `MAINTENANCE` khi còn lịch tương lai
- **Điều kiện**: Xe ID 1 có `ResourceBooking` với `end_time` trong tương lai và status `CONFIRMED`.
- **Request**:
  ```bash
  curl -X PATCH http://localhost:8000/api/v1/trucks/1/status \
    -H "Content-Type: application/json" \
    -d '{"status": "MAINTENANCE", "reason": "Bảo dưỡng"}'
  ```
- **Kỳ vọng**: HTTP 409 Conflict. `error` nêu rõ xe còn lịch phân công, `data.conflicting_bookings` liệt kê danh sách booking cần giải tỏa.

### Kịch bản 5: Chặn xóa cứng khi đã có lịch sử booking (Soft Delete Guard)
- **Request**:
  ```bash
  curl -X DELETE http://localhost:8000/api/v1/trucks/1
  ```
- **Kỳ vọng**: HTTP 400 Bad Request. `error`: "Không thể xóa nguồn lực đã có lịch sử hoạt động. Vui lòng chuyển trạng thái sang INACTIVE."
