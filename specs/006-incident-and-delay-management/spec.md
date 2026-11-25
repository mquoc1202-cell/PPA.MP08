# Feature Specification: TRN-05 Quản lý sự cố và chậm tiến độ (Incident & Delay Management)

**Feature Branch**: `006-incident-and-delay-management`  
**Created**: 2026-11-25  
**Status**: Draft  
**Input**: User description: "tạo module 03_Freight_Transportation.pdf TRN-05 Quản lý sự cố và chậm tiến độ"

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ghi nhận và Đóng Sự cố Vận chuyển (Priority: P1) 🎯 MVP

Là một Điều phối viên (DSP), tôi muốn ghi nhận các sự cố phát sinh trong quá trình vận hành chuyến hàng (hỏng xe, tắc đường nghiêm trọng, tai nạn, sự cố hàng hóa, thời tiết xấu...) và cập nhật kết quả xử lý để các bộ phận nắm bắt tình hình và phối hợp giải quyết kịp thời.

**Why this priority**: Sự cố là thực tế không thể tránh khỏi trong vận tải đường bộ. Việc ghi nhận chính xác loại sự cố, thời điểm phát sinh, mô tả chi tiết, người chịu trách nhiệm xử lý và thời gian dự kiến khắc phục giúp doanh nghiệp duy trì tính minh bạch, hạn chế thiệt hại và có căn cứ giải trình với khách hàng.

**Independent Test**: Có thể kiểm thử độc lập bằng cách chọn một chuyến hàng đang ở trạng thái `ASSIGNED`, `PICKED_UP`, hoặc `IN_TRANSIT`, mở form lập biên bản sự cố, nhập đầy đủ thông tin (loại sự cố, thời điểm, mô tả, người xử lý, dự kiến khắc phục). Hệ thống lưu sự cố ở trạng thái `OPEN`. Sau đó thực hiện đóng sự cố bằng cách nhập kết quả xử lý, chuyển trạng thái sang `RESOLVED`. Kiểm tra chuyến hàng không bị tự động hoàn tất hay tự động đổi cước phí.

**Acceptance Scenarios**:

1. **Given** một chuyến hàng ở trạng thái vận hành (`ASSIGNED`, `PICKED_UP`, hoặc `IN_TRANSIT`),  
   **When** điều phối viên tạo biên bản sự cố mới với các thông tin: Loại sự cố (`issue_type`), Thời điểm phát sinh (`occurred_at`), Mô tả chi tiết (`description`), Người chịu trách nhiệm xử lý (`handled_by`), và Thời gian dự kiến khắc phục (`estimated_resolution_time`),  
   **Then** hệ thống tạo bản ghi sự cố mới ở trạng thái `OPEN`, gán mã tham chiếu sự cố, hiển thị cảnh báo sự cố trên chi tiết chuyến hàng, và ghi nhận sự kiện `ISSUE_LOGGED` vào dòng thời gian vận chuyển.

2. **Given** một sự cố đang ở trạng thái `OPEN`,  
   **When** điều phối viên thực hiện đóng sự cố bằng cách nhập kết quả xử lý (`resolution_notes`) và thời điểm hoàn tất khắc phục,  
   **Then** hệ thống chuyển trạng thái sự cố sang `RESOLVED`, lưu thời điểm đóng, xóa cảnh báo sự cố đang mở trên chuyến hàng (nếu không còn sự cố OPEN nào khác), và ghi nhận sự kiện `ISSUE_RESOLVED` vào dòng thời gian.

3. **Given** một chuyến hàng phát sinh sự cố,  
   **When** sự cố được ghi nhận hoặc giải quyết,  
   **Then** trạng thái vòng đời của chuyến hàng (`status`) KHÔNG bị tự động chuyển sang `COMPLETED` hay trạng thái khác, và giá trị cước phí chuyến hàng KHÔNG bị tự động thay đổi (mọi phát sinh phụ phí nếu có sẽ do bộ phận kinh doanh xử lý theo quy định SAL-08).

---

### User Story 2 - Phát hiện và Cảnh báo Quá hạn Vận hành (Priority: P1)

Là một Điều phối viên (DSP) hoặc Nhà quản lý (MGR), tôi muốn hệ thống tự động phát hiện và cảnh báo cờ "Quá hạn vận hành" (Delayed / Overdue) đối với các chuyến hàng chưa hoàn thành khi thời gian hiện tại đã vượt quá thời điểm kết thúc dự kiến đã cam kết, để có phương án can thiệp khẩn cấp.

**Why this priority**: Chậm trễ giao hàng ảnh hưởng trực tiếp đến uy tín của doanh nghiệp và cam kết dịch vụ (SLA) với khách hàng. Việc phát hiện tự động theo thời gian thực giúp điều phối viên ưu tiên hỗ trợ các chuyến hàng có nguy cơ đổ vỡ cam kết mà không cần rà soát thủ công từng chuyến.

**Independent Test**: Có thể kiểm thử độc lập bằng cách thiết lập thời điểm kết thúc dự kiến (`estimated_end_time`) của một chuyến hàng nhỏ hơn thời điểm hiện tại (`current_time`), trong khi chuyến hàng vẫn ở trạng thái `ASSIGNED`, `PICKED_UP`, hoặc `IN_TRANSIT`. Hệ thống lập tức kích hoạt cờ cảnh báo `DELAYED` (Quá hạn) trên giao diện danh sách chuyến hàng và trang chi tiết với biểu tượng cảnh báo màu đỏ/cam nổi bật. Khi chuyến hàng đã chuyển sang `DELIVERED`, `COMPLETED`, hoặc `CANCELLED`, cờ quá hạn tự động tắt.

**Acceptance Scenarios**:

1. **Given** một chuyến hàng có trạng thái vận hành chưa kết thúc (`UNASSIGNED`, `ASSIGNED`, `PICKED_UP`, hoặc `IN_TRANSIT`),  
   **When** thời gian hiện tại của hệ thống vượt quá thời điểm kết thúc dự kiến (`current_time > estimated_end_time`),  
   **Then** hệ thống tự động gắn cờ hiển thị cảnh báo "Quá hạn vận hành" (`OVERDUE` / `DELAYED`) kèm số giờ/phút đã trễ trên danh mục chuyến hàng và chi tiết chuyến hàng.

2. **Given** một chuyến hàng đang bị gắn cờ quá hạn vận hành,  
   **When** chuyến hàng được ghi nhận chuyển sang trạng thái `DELIVERED`, `COMPLETED`, hoặc `CANCELLED`,  
   **Then** cờ cảnh báo quá hạn vận hành tự động không còn áp dụng đối với chuyến hàng này.

3. **Given** một chuyến hàng bị trễ hạn,  
   **When** hệ thống xác định trạng thái quá hạn vận hành,  
   **Then** hệ thống KHÔNG tự động suy diễn thay đổi trạng thái giao hàng hoặc suy diễn vị trí GPS của xe tải; trạng thái vận chuyển chỉ thay đổi khi có sự kiện nghiệp vụ được ghi nhận thực tế từ điều phối viên / tài xế.

---

### User Story 3 - Điều chỉnh Lùi Thời gian Dự kiến & Kiểm soát Xung đột Lịch Tương lai (Priority: P2)

Là một Điều phối viên (DSP), khi chuyến hàng bị chậm tiến độ hoặc gặp sự cố kéo dài, tôi muốn cập nhật lùi thời điểm kết thúc dự kiến (`estimated_end_time`) và được hệ thống phân tích, cảnh báo chi tiết các lịch trình kế tiếp của xe tải và tài xế bị xung đột (chồng lấn) để chủ động dời hoặc gán lại xe/tài xế khác cho các đơn tương lai.

**Why this priority**: Khi một chuyến hàng bị chậm, xe tải và tài xế không thể giải phóng đúng hạn ban đầu. Nếu không cập nhật lại lịch chiếm dụng và cảnh báo xung đột với các chuyến tương lai, toàn bộ chuỗi điều phối phía sau sẽ bị đổ vỡ dây chuyền và vi phạm nghiêm trọng quy tắc BR-09 (nguồn lực đang bận không được nhận việc mới).

**Independent Test**: Có thể kiểm thử độc lập bằng cách tạo chuyến hàng A có lịch `[T1, T2]` và chuyến hàng B của cùng xe/tài xế có lịch `[T2 + 1h, T3]`. Khi chuyến A gặp sự cố và điều phối viên cập nhật thời gian kết thúc dự kiến thành `T2 + 2h` (chồng lấn vào khung giờ chuyến B): Hệ thống phát hiện xung đột, GIỮ NGUYÊN lịch chuyến A, thông báo cảnh báo chi tiết mã chuyến B bị trùng lịch và hướng dẫn điều phối viên gỡ hoặc đổi phân công cho chuyến B.

**Acceptance Scenarios**:

1. **Given** một chuyến hàng đang vận hành có thời điểm kết thúc dự kiến ban đầu `estimated_end_time`,  
   **When** điều phối viên cập nhật lùi mốc thời gian kết thúc mới `new_estimated_end_time` (muộn hơn mốc cũ) do sự cố hoặc tắc đường,  
   **Then** hệ thống thực hiện kiểm tra lịch trình tương lai của cả Xe tải và Tài xế trong khoảng thời gian gia hạn mới.

2. **Given** việc gia hạn thời gian kết thúc của chuyến hàng hiện tại dẫn đến chồng lấn lịch với một hoặc nhiều booking tương lai của cùng xe tải hoặc tài xế,  
   **When** hệ thống kiểm tra xung đột lịch trình,  
   **Then** hệ thống:  
   - GIỮ NGUYÊN và cập nhật lịch đang có của chuyến hàng hiện tại;  
   - Hiển thị danh sách cảnh báo chi tiết các booking tương lai bị xung đột (mã chuyến, loại dịch vụ vận tải/cho thuê, khoảng thời gian bị chồng lấn);  
   - Yêu cầu điều phối viên chủ động thực hiện gỡ hoặc đổi nguồn lực cho các đơn tương lai bị ảnh hưởng;  
   - Tiếp tục áp dụng quy tắc BR-09: xe tải và tài xế đang bận thực tế sẽ không thể bấm nhận hàng (`PICKED_UP`) cho chuyến kế tiếp.

3. **Given** điều phối viên cập nhật lùi mốc thời gian kết thúc dự kiến,  
   **When** mốc thời gian mới không gây xung đột với bất kỳ lịch tương lai nào,  
   **Then** hệ thống cập nhật `estimated_end_time` của chuyến hàng, kéo dài thời gian kết thúc trong bảng `resource_bookings` tương ứng, ghi nhận sự kiện `SCHEDULE_DELAYED` vào dòng thời gian và xóa bỏ cờ quá hạn nếu mốc mới lớn hơn thời gian hiện tại.

---

### User Story 4 - Nhật ký Sự cố Toàn diện & Tích hợp Dòng Thời gian (Priority: P3)

Là một Điều phối viên (DSP), Trưởng phòng Kinh doanh (SAL), hoặc Quản lý (MGR), tôi muốn theo dõi toàn bộ lịch sử các sự cố phát sinh, tiến độ giải quyết và các lần điều chỉnh lịch trình trên Dòng thời gian (Timeline) và Bảng nhật ký sự cố của chuyến hàng để phục vụ việc tra cứu, đối soát và đánh giá chất lượng dịch vụ.

**Why this priority**: Dữ liệu sự cố và lịch trình là căn cứ pháp lý quan trọng để giải quyết tranh chấp với khách hàng, xác định trách nhiệm bảo hiểm, hoặc tính toán phụ phí phát sinh (nếu có lỗi từ phía khách hàng giữ xe quá giờ).

**Independent Test**: Có thể kiểm thử độc lập bằng cách mở chi tiết một chuyến hàng có phát sinh sự cố và điều chỉnh lịch, kiểm tra bảng "Nhật ký sự cố" hiển thị đầy đủ danh sách các sự cố (mã sự cố, phân loại, mô tả, người phụ trách, thời điểm giải quyết, kết quả giải quyết). Kiểm tra Dòng thời gian lịch sử hiển thị các sự kiện `ISSUE_LOGGED`, `ISSUE_RESOLVED`, `SCHEDULE_DELAYED` với biểu tượng và mốc thời gian chuẩn xác.

**Acceptance Scenarios**:

1. **Given** một chuyến hàng có một hoặc nhiều sự cố đã được lập biên bản,  
   **When** người dùng (DSP, SAL, MGR) xem trang chi tiết chuyến hàng,  
   **Then** hệ thống hiển thị khối "Nhật Ký Sự Cố Chuyến Hàng" với đầy đủ bảng thông tin: Mã sự cố, Loại sự cố, Mô tả chi tiết, Người chịu trách nhiệm, Mốc thời gian phát sinh/giải quyết, Trạng thái (`OPEN` màu đỏ / `RESOLVED` màu xanh lá), và Kết quả xử lý.

2. **Given** các thao tác phát sinh sự cố, khắc phục sự cố hoặc điều chỉnh thời gian chuyến hàng,  
   **When** thao tác được ghi nhận thành công,  
   **Then** hệ thống tự động ghi nhận các sự kiện tương ứng vào bảng `trip_events` (`ISSUE_LOGGED`, `ISSUE_RESOLVED`, `SCHEDULE_DELAYED`) và hiển thị trên Dòng thời gian lịch sử chuyến hàng.

---

### User Story 5 - Bộ Lọc Chuyến Hàng Có Sự Cố/Quá Hạn & Kiểm Soát Phân Quyền RBAC (Priority: P3)

Là một Điều phối viên (DSP), tôi muốn có bộ lọc riêng biệt trên màn hình danh mục chuyến hàng để nhanh chóng lọc ra các chuyến "Đang có sự cố" hoặc "Quá hạn vận hành" nhằm xử lý ưu tiên; đồng thời hệ thống phải đảm bảo chỉ vai trò `DSP` mới có quyền can thiệp ghi nhận/sửa đổi sự cố và gia hạn lịch, các vai trò `SAL` và `MGR` chỉ có quyền xem (Read-only).

**Why this priority**: Khi đội xe vận hành hàng chục chuyến đồng thời, điều phối viên cần tập trung vào các trường hợp bất thường (Management by Exception). Kiểm soát quyền truy cập chặt chẽ ngăn ngừa các bộ phận khác can thiệp sai lệch vào quy trình vận hành.

**Independent Test**: Có thể kiểm thử độc lập bằng cách đăng nhập tài khoản `SAL` hoặc `MGR`, truy cập danh sách và chi tiết chuyến hàng: người dùng xem được cờ cảnh báo quá hạn và nhật ký sự cố nhưng không nhìn thấy các nút "Báo Cáo Sự Cố", "Đóng Sự Cố", hoặc "Gia Hạn Lịch"; nếu gửi request POST can thiệp trực tiếp qua API, hệ thống trả về mã lỗi HTTP 403 Forbidden.

**Acceptance Scenarios**:

1. **Given** người dùng truy cập trang danh mục chuyến hàng `/trips`,  
   **When** người dùng bấm chọn tab lọc "Có Sự Cố" hoặc "Quá Hạn Vận Hành",  
   **Then** hệ thống hiển thị danh sách các chuyến hàng đang có sự cố `OPEN` hoặc các chuyến có `current_time > estimated_end_time` mà chưa hoàn tất.

2. **Given** người dùng đăng nhập với vai trò `SAL` hoặc `MGR`,  
   **When** truy cập vào màn hình chi tiết chuyến hàng có sự cố hoặc quá hạn,  
   **Then** hệ thống hiển thị thông tin ở chế độ chỉ đọc (Read-only), ẩn các nút chức năng thao tác ghi nhận sự cố, đóng sự cố, điều chỉnh lịch; nếu cố tình gửi request ghi thì bị từ chối với HTTP 403 Forbidden.

3. **Given** người dùng đăng nhập với vai trò `DSP`,  
   **When** truy cập vào màn hình chi tiết chuyến hàng,  
   **Then** hệ thống hiển thị đầy đủ các nút chức năng "Báo Cáo Sự Cố", "Giải Quyết Sự Cố", và "Điều Chỉnh Lịch Dự Kiến".

---

### Edge Cases

- **Chuyến hàng phát sinh đồng thời nhiều sự cố**: Một chuyến hàng có thể phát sinh nhiều sự cố khác nhau (ví dụ: vừa bị hỏng lốp xe vừa bị kẹt phà). Cảnh báo sự cố của chuyến hàng chỉ biến mất khi TẤT CẢ các sự cố liên quan đều đã được đóng (`RESOLVED` hoặc `CANCELLED`).
- **Gia hạn thời gian kết thúc về quá khứ**: Điều phối viên nhập thời điểm kết thúc dự kiến mới nhỏ hơn thời điểm bắt đầu chuyến hoặc nhỏ hơn thời điểm hiện tại ➔ Hệ thống từ chối cập nhật với thông báo lỗi rõ ràng.
- **Xe tải hoặc tài xế bị trùng lịch với hợp đồng cho thuê xe**: Khi gia hạn thời gian kết thúc chuyến hàng, việc kiểm tra xung đột phải quét qua cả các hợp đồng thuê xe (`service_type = 'RENTAL'`) chứ không chỉ riêng các chuyến vận tải hàng hóa.
- **Sự cố giao hàng thất bại (từ TRN-04)**: Khi ghi nhận giao hàng thất bại ở TRN-04, hệ thống đã tự động tạo một bản ghi `TripIssue` loại `DELIVERY_FAILED` với trạng thái `OPEN`. Bản ghi này phải xuất hiện đầy đủ trong giao diện quản lý của TRN-05 để điều phối viên có thể cập nhật kết quả xử lý và đóng sự cố.
- **Hệ thống chạy qua thời điểm giao hẹn khi điều phối viên không mở trình duyệt**: Khi tính toán cờ quá hạn (`is_delayed`), hệ thống dựa trên truy vấn so sánh `current_time > estimated_end_time` trong cơ sở dữ liệu/API, đảm bảo tính toán động chính xác mà không phụ thuộc vào tiến trình nền giả lập.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI cho phép Điều phối viên (`DSP`) ghi nhận sự cố cho chuyến hàng với các trường bắt buộc: loại sự cố (`issue_type`), thời điểm phát sinh (`occurred_at`), mô tả chi tiết (`description`), người phụ trách xử lý (`handled_by`), và thời điểm dự kiến khắc phục (`estimated_resolution_time`).
- **FR-002**: Hệ thống PHẢI hỗ trợ các danh mục phân loại sự cố chuẩn hóa: `VEHICLE_BREAKDOWN` (Hỏng hóc phương tiện), `TRAFFIC_CONGESTION` (Kẹt xe/Ùn tắc giao thông), `ACCIDENT` (Tai nạn giao thông), `CARGO_DAMAGE` (Hư hại/Sự cố hàng hóa), `WEATHER_DELAY` (Thời tiết bất lợi), `DELIVERY_FAILED` (Giao hàng thất bại), và `OTHER` (Sự cố khác).
- **FR-003**: Bản ghi sự cố mới tạo PHẢI mặc định có trạng thái `OPEN`.
- **FR-004**: Hệ thống PHẢI cho phép Điều phối viên (`DSP`) đóng sự cố chuyển trạng thái từ `OPEN` sang `RESOLVED`, bắt buộc nhập thông tin kết quả xử lý (`resolution_notes`) và ghi nhận thời điểm đóng (`resolved_at`).
- **FR-005**: Hệ thống PHẢI tự động xác định và hiển thị cờ cảnh báo "Quá hạn vận hành" (`is_delayed = True`) khi thời gian hiện tại vượt quá mốc kết thúc dự kiến (`current_time > estimated_end_time`) đối với các chuyến hàng chưa ở trạng thái `DELIVERED`, `COMPLETED`, hoặc `CANCELLED`.
- **FR-006**: Hệ thống PHẢI tự động tắt cờ cảnh báo quá hạn khi chuyến hàng được chuyển sang trạng thái `DELIVERED`, `COMPLETED`, hoặc `CANCELLED`.
- **FR-007**: Hệ thống PHẢI cho phép Điều phối viên (`DSP`) cập nhật lùi mốc thời gian kết thúc dự kiến (`estimated_end_time`) của chuyến hàng khi gặp chậm trễ hoặc sự cố kéo dài.
- **FR-008**: Khi cập nhật thời gian kết thúc dự kiến, hệ thống PHẢI kiểm tra lại lịch trình tương lai của cả Xe tải và Tài xế; nếu phát hiện xung đột (chồng lấn lịch với booking kế tiếp), hệ thống PHẢI GIỮ NGUYÊN lịch đang cập nhật của chuyến hiện tại và HIỂN THỊ DANH SÁCH CÁC BOOKING BỊ XUNG ĐỘT để điều phối viên chủ động xử lý đổi hoặc dời lịch tương lai.
- **FR-009**: Hệ thống PHẢI tiếp tục duy trì quy tắc BR-09: xe tải và tài xế đang thực hiện chuyến hàng (`IN_PROGRESS`) chưa hoàn tất sẽ bị chặn tuyệt đối không cho phép bấm nhận hàng (`PICKED_UP`) ở bất kỳ chuyến hàng kế tiếp nào.
- **FR-010**: Hệ thống TUYỆT ĐỐI KHÔNG tự động chuyển trạng thái vòng đời của chuyến hàng sang `COMPLETED` hoặc tự ý thay đổi cước phí chuyến hàng khi phát sinh sự cố; mọi chi phí phát sinh (nếu có) phải do bộ phận kinh doanh xử lý theo quy định SAL-08.
- **FR-011**: Hệ thống TUYỆT ĐỐI KHÔNG tự động suy diễn vị trí GPS hoặc tự suy diễn trạng thái giao hàng từ thời gian dự kiến; trạng thái chỉ được phép thay đổi theo các sự kiện nghiệp vụ thực tế được ghi nhận.
- **FR-012**: Hệ thống PHẢI ghi nhận các sự kiện `ISSUE_LOGGED`, `ISSUE_RESOLVED`, và `SCHEDULE_DELAYED` vào bảng dòng thời gian `TripEvent` để lưu vết kiểm toán bất biến.
- **FR-013**: Hệ thống PHẢI phân quyền nghiêm ngặt: chỉ người dùng vai trò `DSP` mới có quyền lập sự cố, đóng sự cố, và cập nhật thời gian dự kiến; người dùng vai trò `SAL` và `MGR` chỉ có quyền xem (Read-only), trả về mã HTTP 403 Forbidden nếu cố tình thao tác ghi.

---

### Key Entities *(include if feature involves data)*

- **TripIssue (Nhật ký Sự cố)**: Đại diện cho một sự cố phát sinh liên quan đến chuyến hàng.
  - `id`: Định danh duy nhất của sự cố.
  - `trip_id`: Khóa ngoại tham chiếu đến chuyến hàng (`Trip`).
  - `issue_type`: Loại sự cố (`VEHICLE_BREAKDOWN`, `TRAFFIC_CONGESTION`, `ACCIDENT`, `CARGO_DAMAGE`, `WEATHER_DELAY`, `DELIVERY_FAILED`, `OTHER`).
  - `description`: Mô tả chi tiết nguyên nhân và hiện trạng sự cố.
  - `occurred_at`: Thời điểm thực tế phát sinh sự cố.
  - `handled_by`: Họ tên/chức vụ người phụ trách xử lý sự cố.
  - `estimated_resolution_time`: Thời điểm dự kiến khắc phục xong sự cố.
  - `status`: Trạng thái sự cố (`OPEN`, `RESOLVED`, `CANCELLED`).
  - `resolution_notes`: Ghi chú kết quả xử lý và giải pháp khắc phục khi đóng sự cố.
  - `resolved_at`: Thời điểm sự cố được đánh dấu giải quyết thành công.
  - `reported_by_user_id`: Khóa ngoại tham chiếu người dùng lập biên bản sự cố.
  - `created_at`: Thời điểm hệ thống ghi nhận bản ghi sự cố.

- **Trip (Chuyến hàng - Mở rộng hiển thị)**:
  - `estimated_end_time`: Mốc thời gian kết thúc cam kết / dự kiến. Có thể được điều phối viên gia hạn khi gặp sự cố trễ tiến độ.
  - `is_delayed`: Thuộc tính tính toán động (`current_time > estimated_end_time` và status không thuộc `DELIVERED`, `COMPLETED`, `CANCELLED`).
  - `has_open_issues`: Thuộc tính tính toán động kiểm tra chuyến hàng có sự cố nào đang ở trạng thái `OPEN` hay không.

- **ResourceBooking (Lịch Chiếm dụng Nguồn lực)**:
  - `start_time`, `end_time`: Khoảng thời gian chiếm dụng nguồn lực xe tải và tài xế. Khi chuyến hàng được gia hạn `estimated_end_time`, bản ghi booking tương ứng được cập nhật `end_time` mới.

- **TripEvent (Dòng Thời Gian Lịch Sử)**:
  - Bổ sung các loại sự kiện kiểm toán: `ISSUE_LOGGED`, `ISSUE_RESOLVED`, `SCHEDULE_DELAYED`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các sự cố phát sinh được lập biên bản và hiển thị tức thời trên trang chi tiết chuyến hàng trong vòng dưới 1 giây.
- **SC-002**: 100% các chuyến hàng chưa hoàn tất có `current_time > estimated_end_time` được phát hiện và gắn cờ cảnh báo quá hạn vận hành (`DELAYED`) chính xác mà không cần quét thủ công.
- **SC-003**: Khi điều phối viên điều chỉnh lùi thời gian kết thúc dự kiến, hệ thống phát hiện chính xác 100% các booking tương lai của cùng xe tải và tài xế bị xung đột thời gian, hiển thị danh sách xung đột trong vòng dưới 500ms.
- **SC-004**: Đảm bảo 100% tính toàn vẹn trạng thái và doanh thu: không có chuyến hàng nào bị tự động đổi trạng thái sang `COMPLETED` hoặc tự động đổi giá cước khi ghi nhận sự cố.
- **SC-005**: 100% các thao tác ghi nhận sự cố, đóng sự cố, và lùi lịch trình được bảo vệ phân quyền chặt chẽ (chặn 100% các thao tác trái phép từ vai trò `SAL` và `MGR` với mã HTTP 403 Forbidden).

---

## Assumptions

- Thông tin về người phụ trách xử lý sự cố (`handled_by`) có thể là tài xế, điều phối viên hiện trường, hoặc đơn vị cứu hộ bên ngoài, được lưu dưới dạng chuỗi văn bản linh hoạt kèm thông tin liên hệ.
- Các phụ phí phát sinh từ sự cố (như phí bốc xếp thêm, phí lưu xe qua đêm, chi phí xe cẩu cứu hộ) không được hệ thống vận tải tự động cộng vào giá chuyến hàng, mà sẽ được bộ phận kinh doanh xử lý trong phân hệ thanh toán / hợp đồng theo quy tắc SAL-08.
- Cờ cảnh báo quá hạn vận hành là thuộc tính tính toán thời gian thực dựa trên đồng hồ máy chủ cơ sở dữ liệu (`datetime.now()`), không yêu cầu cấu hình thêm tiến độ chạy ngầm cronjob riêng biệt để cập nhật cờ.
- Quy tắc kiểm tra xung đột khi gia hạn thời gian kế thừa toàn bộ cơ chế khóa và kiểm tra trùng lịch đã được xây dựng tại phân hệ TRN-02 (`booking_repo.py` và `dispatch_service.py`).
