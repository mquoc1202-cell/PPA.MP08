# Feature Specification: 003-trip-dispatch-and-conflict-management

**Feature Branch**: `003-trip-dispatch-and-conflict-management`  
**Created**: 2026-11-23  
**Status**: Draft  
**Input**: User description: "Tạo module TRN-02 Điều phối chuyến hàng và quản lý trùng lịch"  
**Business Reference**: `03_Freight_Transportation.pdf` (Mục TRN-02), Hiến pháp dự án (`.specify/memory/constitution.md`)  

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Phân công Xe và Tài xế cho Chuyến hàng mới (Priority: P1) 🎯 MVP

Là một Điều phối viên (DSP), tôi muốn phân công một xe tải đủ tải trọng và một tài xế phù hợp cho đơn vận chuyển đã xác nhận trong một khung thời gian cụ thể, để chuyến hàng có thể được thực hiện đúng kế hoạch mà không bị quá tải hay xung đột với công việc khác.

**Why this priority**: Đây là giá trị cốt lõi nhất của quy trình vận tải hàng hóa (TRN-02). Nếu không có phân công hợp lệ, chuyến hàng không thể chuyển sang trạng thái sẵn sàng thực hiện (`ASSIGNED`) và không thể bước sang giai đoạn nhận hàng (`PICKED_UP`).

**Independent Test**: Chọn một chuyến hàng ở trạng thái `UNASSIGNED`, phân công một xe có tải trọng lớn hơn hoặc bằng khối lượng hàng hóa và một tài xế rảnh trong khung giờ dự kiến. Kiểm tra chuyến chuyển sang trạng thái `ASSIGNED`, cả xe và tài xế đều được ghi nhận lịch chiếm dụng tương ứng.

**Acceptance Scenarios**:

1. **Given** một chuyến hàng ở trạng thái `UNASSIGNED` có khối lượng hàng hóa 5,000 kg và thời gian dự kiến từ 08:00 đến 17:00 ngày mai,  
   **When** điều phối viên phân công xe tải 8,000 kg đang hoạt động (`ACTIVE`) và tài xế đang sẵn sàng (`ACTIVE`), cả hai đều không vướng lịch trình nào khác trong khung giờ trên,  
   **Then** hệ thống cập nhật trạng thái chuyến hàng sang `ASSIGNED`, xác lập thông tin xe và tài xế cho chuyến, đồng thời tạo lịch chiếm dụng (booking) xác nhận cho cả xe và tài xế.

2. **Given** một chuyến hàng có khối lượng hàng 6,000 kg,  
   **When** điều phối viên cố tình chọn xe tải có tải trọng chỉ 5,000 kg,  
   **Then** hệ thống từ chối phân công, hiển thị cảnh báo quá tải trọng quy định, giữ nguyên trạng thái chuyến là `UNASSIGNED` và không tạo bất kỳ lịch chiếm dụng nào.

3. **Given** một chuyến hàng cần thực hiện từ 09:00 đến 15:00 ngày mai,  
   **When** điều phối viên chọn xe hoặc tài xế đã bị chiếm dụng trong khung giờ chồng lấn (do đơn vận tải khác hoặc đơn cho thuê xe),  
   **Then** hệ thống từ chối yêu cầu, hiển thị thông tin chi tiết về mã đơn và khung giờ bị xung đột, giữ nguyên trạng thái `UNASSIGNED` và tuyệt đối không tạo lịch chiếm dụng một phần (nếu xe bị trùng thì tài xế cũng không bị giữ lịch).

4. **Given** một xe tải đang ở trạng thái bảo dưỡng (`MAINTENANCE`) hoặc ngừng hoạt động (`INACTIVE`), hoặc một tài xế đang tạm nghỉ (`INACTIVE`),  
   **When** điều phối viên thực hiện phân công,  
   **Then** hệ thống từ chối nguồn lực không khả dụng và yêu cầu chọn nguồn lực đang sẵn sàng hoạt động.

---

### User Story 2 - Thay đổi hoặc Hủy Phân công Nguồn lực trước khi Nhận hàng (Priority: P2)

Là một Điều phối viên, tôi muốn có thể thay đổi xe hoặc tài xế đã gán, hoặc hủy bỏ phân công đưa chuyến về lại trạng thái chưa phân công khi có phát sinh thay đổi kế hoạch, để có thể linh hoạt điều chỉnh nguồn lực trước khi chuyến bắt đầu lăn bánh nhận hàng.

**Why this priority**: Trong thực tế vận hành vận tải, việc xe gặp trục trặc kỹ thuật đột xuất hoặc tài xế có lý do cá nhân bất khả kháng trước giờ khởi hành xảy ra thường xuyên; điều phối viên bắt buộc phải có công cụ điều chỉnh phân công mà không làm gián đoạn toàn bộ đơn hàng.

**Independent Test**: Chọn một chuyến đang ở trạng thái `ASSIGNED`, thực hiện đổi sang một xe khác hợp lệ; kiểm tra lịch của xe cũ được giải phóng hoàn toàn và lịch của xe mới được xác lập nhất quán. Sau đó thử đổi phân công trên một chuyến đã ở trạng thái `PICKED_UP` để kiểm tra cơ chế khóa chặn.

**Acceptance Scenarios**:

1. **Given** một chuyến hàng ở trạng thái `ASSIGNED` (chưa nhận hàng `PICKED_UP`),  
   **When** điều phối viên chọn thay đổi sang một xe khác đủ điều kiện tải trọng và còn rảnh lịch,  
   **Then** hệ thống giải phóng lịch chiếm dụng của xe cũ, thiết lập lịch chiếm dụng cho xe mới, và cập nhật thông tin chuyến hàng thành công.

2. **Given** một chuyến hàng ở trạng thái `ASSIGNED`,  
   **When** điều phối viên thực hiện thao tác gỡ bỏ phân công (hủy phân công),  
   **Then** hệ thống giải phóng toàn bộ lịch chiếm dụng của cả xe và tài xế, đồng thời chuyển trạng thái chuyến hàng trở về `UNASSIGNED`.

3. **Given** một chuyến hàng đang ở trạng thái `ASSIGNED`,  
   **When** điều phối viên cố gắng đổi sang một tài xế mới nhưng tài xế này bị trùng lịch,  
   **Then** hệ thống báo lỗi xung đột lịch trình, giữ nguyên phân công tài xế cũ và lịch trình cũ không bị thay đổi (không để xảy ra trạng thái dở dang).

4. **Given** một chuyến hàng đã chuyển sang trạng thái `PICKED_UP` (đã nhận hàng) hoặc các trạng thái sau đó (`IN_TRANSIT`, `DELIVERED`, `COMPLETED`),  
   **When** người dùng cố gắng đổi xe, đổi tài xế hoặc gỡ phân công,  
   **Then** hệ thống kiên quyết ngăn chặn thao tác và thông báo chuyến hàng đã bắt đầu thực hiện, không được phép can thiệp phân công ngoài quy trình xử lý sự cố.

---

### User Story 3 - Kiểm soát Xung đột Đồng thời giữa các Điều phối viên (Priority: P2)

Là một Quản trị viên vận tải, tôi muốn hệ thống có cơ chế kiểm soát đồng thời khi nhiều điều phối viên cùng thao tác phân công vào cùng một thời điểm, để đảm bảo không bao giờ xảy ra tình trạng hai chuyến hàng khác nhau cùng giữ chung một xe hoặc một tài xế trong cùng một khoảng thời gian.

**Why this priority**: Đảm bảo tính toàn vẹn dữ liệu và ngăn chặn tuyệt đối tranh chấp tài nguyên (race condition) giữa các điều phối viên trong giờ cao điểm điều phối đơn vận chuyển.

**Independent Test**: Mô phỏng 2 phiên điều phối viên cùng lúc gửi yêu cầu gán 1 xe vào cùng một khoảng thời gian trùng nhau; xác nhận chỉ đúng 1 điều phối viên thành công và điều phối viên còn lại nhận được thông báo xung đột lịch trình để chọn nguồn lực khác.

**Acceptance Scenarios**:

1. **Given** hai điều phối viên A và B cùng mở form điều phối hai chuyến hàng khác nhau nhưng cùng chọn chung Xe X và Tài xế Y trong khung giờ từ 13:00 đến 18:00 ngày mai,  
   **When** cả hai điều phối viên gửi lệnh phân công gần như đồng thời,  
   **Then** hệ thống chỉ chấp thuận duy nhất một yêu cầu gửi đến trước thành công (chuyển sang `ASSIGNED`), yêu cầu gửi đến sau bị từ chối với thông báo "Nguồn lực đã bị điều phối viên khác chiếm dụng trong khoảng thời gian này, vui lòng kiểm tra lại lịch trình."

---

### User Story 4 - Tra cứu Lịch trình Chiếm dụng của Xe và Tài xế (Priority: P3)

Là một Điều phối viên hoặc Nhân viên kinh doanh, tôi muốn xem lịch trình chiếm dụng của từng xe và từng tài xế dưới dạng danh sách rõ ràng theo ngày hoặc khoảng ngày, để dễ dàng nắm bắt thời gian rảnh/bận và lên kế hoạch nhận đơn vận chuyển mới.

**Why this priority**: Giúp tăng năng suất làm việc của điều phối viên, giảm thiểu thời gian đoán mò hoặc chọn thử gây ra lỗi trùng lịch; đồng thời hỗ trợ bộ phận kinh doanh tra cứu khả năng đáp ứng của đội xe.

**Independent Test**: Mở màn hình tra cứu lịch trình, lọc theo biển số xe hoặc mã tài xế và chọn khoảng ngày; kiểm tra hệ thống hiển thị danh sách tất cả các booking kèm mã đơn tham chiếu, loại dịch vụ (Vận tải hàng hóa hoặc Cho thuê xe), thời điểm bắt đầu và thời điểm kết thúc.

**Acceptance Scenarios**:

1. **Given** người dùng chọn xem lịch trình của Xe tải `29C-123.45` trong tuần tới,  
   **When** nhấn nút tìm kiếm hoặc tra cứu,  
   **Then** hệ thống liệt kê danh sách toàn bộ các khoảng thời gian xe bị chiếm dụng, bao gồm cả chuyến vận tải hàng hóa và hợp đồng cho thuê xe, hiển thị rõ mã đơn tham chiếu và trạng thái lịch.

2. **Given** một xe hoặc tài xế hoàn toàn không có lịch chiếm dụng nào trong khoảng ngày được chọn,  
   **When** người dùng tra cứu,  
   **Then** hệ thống hiển thị thông báo trạng thái sẵn sàng (trống lịch 100% trong khoảng thời gian này).

---

## Edge Cases

- **Khoảng thời gian không hợp lệ**: Thời gian kết thúc dự kiến nhỏ hơn hoặc bằng thời gian bắt đầu dự kiến (`end_time <= start_time`), hoặc thời gian bắt đầu nằm trong quá khứ so với thời điểm phân công ➔ Hệ thống từ chối và yêu cầu nhập lại mốc thời gian hợp lệ.
- **Trùng lịch chéo loại dịch vụ**: Xe tải bị chiếm dụng bởi một hợp đồng cho thuê xe (không phải chuyến vận chuyển thông thường) trong cùng khung giờ ➔ Hệ thống vẫn phải nhận diện xung đột và ngăn chặn phân công theo quy định BR-07.
- **Khối lượng hàng hóa bằng đúng tải trọng**: Khối lượng hàng `5,000 kg` trên xe tải trọng đúng `5,000 kg` ➔ Phân công thành công (tải trọng bằng mức tối đa cho phép). Khối lượng `5,001 kg` ➔ Từ chối ngay lập tức.
- **Sự cố đứt quãng kết nối trong quá trình lưu dữ liệu**: Quá trình phân công gặp sự cố giữa chừng sau khi gán xe nhưng trước khi gán tài xế ➔ Cơ chế giao dịch nguyên tử tự động hoàn tác toàn bộ, đảm bảo không lưu trạng thái dở dang.
- **Phân quyền truy cập**: Người dùng có vai trò Kinh doanh (`SAL`) hoặc Quản lý (`MGR`) cố tình gọi các thao tác phân công hoặc đổi lịch ➔ Hệ thống chặn quyền truy cập và hiển thị thông báo quyền hạn bị giới hạn.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI cho phép điều phối viên xem danh sách các chuyến hàng cần điều phối (trạng thái `UNASSIGNED`).
- **FR-002**: Hệ thống PHẢI cho phép phân công một xe tải và một tài xế cho một chuyến hàng ở trạng thái `UNASSIGNED`, kèm theo khoảng thời gian chiếm dụng dự kiến `[start_time, end_time]`.
- **FR-003**: Hệ thống PHẢI kiểm tra tải trọng xe: chỉ cho phép phân công nếu tải trọng tối đa của xe lớn hơn hoặc bằng khối lượng hàng hóa của chuyến hàng (`capacity_kg >= cargo_weight_kg`) theo BR-06.
- **FR-004**: Hệ thống PHẢI kiểm tra trạng thái hoạt động: chỉ cho phép chọn xe đang ở trạng thái `ACTIVE` và tài xế đang ở trạng thái `ACTIVE`.
- **FR-005**: Hệ thống PHẢI kiểm tra xung đột trùng lịch: không cho phép phân công nếu xe hoặc tài xế đã có lịch chiếm dụng khác (cả vận tải hàng hóa lẫn cho thuê) trong khoảng thời gian chồng lấn `[start_time, end_time]` theo BR-07 và BR-08.
- **FR-006**: Khi phân công thành công, hệ thống PHẢI chuyển trạng thái chuyến hàng từ `UNASSIGNED` sang `ASSIGNED`, đồng thời tự động tạo 2 bản ghi lịch chiếm dụng (`ResourceBooking`) cho xe và tài xế ở trạng thái xác nhận (`CONFIRMED`).
- **FR-007**: Hệ thống PHẢI đảm bảo tính nguyên tử: nếu kiểm tra phát hiện xe hoặc tài xế không hợp lệ (quá tải, không khả dụng, hoặc trùng lịch), hệ thống PHẢI từ chối toàn bộ và TUYỆT ĐỐI KHÔNG tạo lịch chiếm dụng một phần.
- **FR-008**: Hệ thống PHẢI cho phép điều phối viên thay đổi xe, thay đổi tài xế, hoặc hủy phân công đưa chuyến về lại `UNASSIGNED` KHI VÀ CHỈ KHI chuyến đang ở trạng thái `ASSIGNED` (trước thời điểm nhận hàng `PICKED_UP`).
- **FR-009**: Khi thay đổi phân công thành công, hệ thống PHẢI tự động giải phóng lịch chiếm dụng cũ và xác lập lịch chiếm dụng mới nhất quán; nếu đổi thất bại thì PHẢI giữ nguyên phân công cũ.
- **FR-010**: Hệ thống PHẢI kiên quyết ngăn chặn mọi thao tác đổi hoặc gỡ phân công khi chuyến hàng đã chuyển sang trạng thái `PICKED_UP`, `IN_TRANSIT`, `DELIVERED`, hoặc `COMPLETED`.
- **FR-011**: Hệ thống PHẢI áp dụng cơ chế khóa đồng thời (Concurrency Lock) để đảm bảo khi 2 điều phối viên cùng phân công 1 nguồn lực vào cùng một thời điểm, chỉ duy nhất 1 thao tác thành công, thao tác còn lại nhận thông báo lỗi rõ ràng.
- **FR-012**: Hệ thống PHẢI cung cấp màn hình tra cứu danh sách lịch trình nguồn lực theo ngày và khoảng ngày, thể hiện rõ mã đơn tham chiếu, loại dịch vụ và khung giờ chiếm dụng.
- **FR-013**: Hệ thống PHẢI phân định quyền hạn: chỉ vai trò `DSP` mới được thực hiện các thao tác phân công, thay đổi hoặc hủy phân công; các vai trò `SAL` và `MGR` chỉ có quyền tra cứu (chỉ đọc).

---

### Key Entities *(include if feature involves data)*

- **Chuyến Hàng (Trip)**:
  - Đại diện cho một đơn vận chuyển hàng hóa cần thực hiện.
  - Các thuộc tính chính: Mã chuyến (`reference_code`), Người gửi (`sender_name`, `sender_phone`), Điểm lấy hàng (`pickup_address`), Điểm giao hàng (`delivery_address`), Khối lượng hàng hóa (`cargo_weight_kg`), Loại hàng hóa (`cargo_type`), Thời gian bắt đầu dự kiến (`estimated_start_time`), Thời gian kết thúc dự kiến (`estimated_end_time`), Trạng thái chuyến (`UNASSIGNED`, `ASSIGNED`, `PICKED_UP`, `IN_TRANSIT`, `DELIVERED`, `COMPLETED`, `CANCELLED`), Mã xe được phân công (`assigned_truck_id`), Mã tài xế được phân công (`assigned_driver_id`), Ghi chú điều phối.

- **Lịch Chiếm Dụng Nguồn Lực (ResourceBooking)**:
  - Đại diện cho khoảng thời gian một nguồn lực (xe hoặc tài xế) bị chiếm dụng bởi một chuyến hàng hoặc dịch vụ.
  - Các thuộc tính chính: Loại nguồn lực (`TRUCK` hoặc `DRIVER`), Định danh nguồn lực (`resource_id`), Mã đơn tham chiếu (`reference_code`), Loại dịch vụ (`FREIGHT` - Vận tải hàng hóa, hoặc `RENTAL` - Thuê xe), Thời gian bắt đầu (`start_time`), Thời gian kết thúc (`end_time`), Trạng thái booking (`CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`).

- **Đội Xe (Truck) & Tài Xế (Driver)**:
  - Nguồn lực vận tải đã được quản lý từ module TRN-01, liên kết với Chuyến hàng và Lịch chiếm dụng.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các yêu cầu phân công vi phạm tải trọng (`cargo_weight_kg > capacity_kg`) hoặc có khung thời gian trùng lấn với lịch trình đã có đều bị phát hiện và ngăn chặn thành công trước khi lưu dữ liệu.
- **SC-002**: Tỷ lệ xảy ra lịch chiếm dụng một phần (chỉ gán được xe mà không gán được tài xế hoặc ngược lại khi có lỗi) đạt **chính xác 0%**.
- **SC-003**: Trong môi trường có nhiều điều phối viên thao tác đồng thời trên cùng một xe/tài xế, **100% các trường hợp xung đột thời gian** được nhận diện an toàn mà không làm sai lệch hay nhân đôi dữ liệu lịch trình.
- **SC-004**: Thời gian một điều phối viên thực hiện phân công thành công cho một chuyến hàng đạt dưới **45 giây** trên giao diện web.
- **SC-005**: 100% các chuyến hàng đã bước vào giai đoạn thực hiện (`PICKED_UP` trở đi) được bảo vệ tuyệt đối không thể bị hủy hoặc thay đổi phân công tùy tiện trên giao diện và API.

---

## Assumptions

- **Ước lượng thời gian**: Khoảng thời gian chiếm dụng `[start_time, end_time]` do điều phối viên chủ động ước lượng và nhập vào hệ thống dựa trên lộ trình và kinh nghiệm thực tế; hệ thống không tự động tính toán thời gian di chuyển qua bản đồ GPS.
- **Một chuyến cho một đơn**: Mỗi chuyến hàng chỉ phục vụ cho một đơn hàng vận tải cụ thể (mối quan hệ 1:1), không hỗ trợ ghép nhiều đơn lẻ lên cùng một chuyến trong phiên bản này.
- **Nguồn lực hợp lệ**: Dữ liệu xe và tài xế đã được quản lý và chuẩn hóa đầy đủ từ module TRN-01; hệ thống sử dụng lại toàn bộ cấu trúc định danh và trạng thái sẵn sàng từ TRN-01.
- **Quyền hạn vai trò**: Hệ thống xác thực và nhận diện vai trò người dùng (`DSP`, `SAL`, `MGR`) thông qua phân hệ xác thực đã hoàn thiện ở module 002.
