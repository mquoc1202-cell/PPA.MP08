# Feature Specification: TRN-04 Xác nhận giao hàng và hoàn tất (Delivery Confirmation & Trip Completion)

**Feature Branch**: `005-delivery-and-completion`

**Created**: 2026-11-25

**Status**: Draft

**Input**: User description: "Tạo module TRN-04 Xác nhận giao hàng và hoàn tất"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ghi nhận Giao hàng Thành công kèm Bằng chứng POD (Priority: P1) 🎯 MVP

Là điều phối viên, tôi muốn ghi nhận giao hàng thực tế tại điểm giao kèm chứng từ bằng chứng giao nhận (Proof of Delivery - POD) để xác nhận hàng hóa đã được bàn giao cho người nhận an toàn và hợp lệ, chuyển chuyến hàng sang trạng thái `DELIVERED`.

**Why this priority**: Đây là mốc nghiệp vụ then chốt xác nhận nghĩa vụ vận chuyển đã hoàn thành, làm căn cứ pháp lý và đối soát cước với khách hàng. Thiếu mốc này đơn hàng không thể hoàn tất.

**Independent Test**: Có thể kiểm thử độc lập bằng cách chọn một chuyến hàng đang ở trạng thái `IN_TRANSIT`, gửi thông tin giao hàng gồm thời điểm giao, họ tên người nhận, kết quả thành công và tải lên tệp bằng chứng hợp lệ (PDF/JPG/PNG). Kiểm tra trạng thái chuyến đổi sang `DELIVERED`, tệp bằng chứng được liên kết và thông tin người nhận được lưu trữ chính xác.

**Acceptance Scenarios**:

1. **Given** một chuyến hàng đang ở trạng thái `IN_TRANSIT`, **When** điều phối viên nhập thời điểm giao hàng thực tế ($\ge$ thời điểm nhận hàng), họ tên người nhận, kết quả "Giao thành công" (`SUCCESS`) và tải lên ít nhất một tệp bằng chứng (PDF, JPG, hoặc PNG), **Then** chuyến hàng được chuyển sang trạng thái `DELIVERED`, tệp bằng chứng được lưu an toàn, và sự kiện chuyển trạng thái được ghi lại vào dòng thời gian.
2. **Given** một chuyến hàng đang ở bất kỳ trạng thái nào khác `IN_TRANSIT` (như `UNASSIGNED`, `ASSIGNED`, hoặc `PICKED_UP`), **When** điều phối viên cố gắng gửi yêu cầu xác nhận giao hàng, **Then** hệ thống từ chối và thông báo chuyến hàng chưa đủ điều kiện giao hàng (bảo toàn tính toàn vẹn máy trạng thái).
3. **Given** một chuyến hàng đang ở `IN_TRANSIT`, **When** điều phối viên xác nhận giao hàng mà không tải lên bất kỳ tệp bằng chứng nào (danh sách tệp rỗng), **Then** hệ thống từ chối xác nhận và yêu cầu bắt buộc phải có ít nhất một tệp chứng từ giao hàng.
4. **Given** chuyến hàng đang ở `IN_TRANSIT`, **When** thời điểm giao hàng được nhập trước thời điểm nhận hàng thực tế, **Then** hệ thống từ chối và cảnh báo mốc thời gian không hợp lệ.

---

### User Story 2 - Chốt Hoàn tất Chuyến hàng và Giải phóng Nguồn lực (Priority: P1)

Là điều phối viên, tôi muốn chốt hoàn tất (`COMPLETED`) chuyến hàng sau khi đã giao hàng và giải phóng xe tải cùng tài xế, để nguồn lực sẵn sàng nhận nhiệm vụ vận tải tiếp theo mà không bị chặn bởi các quy tắc xung đột lịch.

**Why this priority**: Giải phóng nguồn lực thực tế là yêu cầu cốt lõi trong chuỗi vận hành đội xe; nếu không hoàn tất và giải phóng xe/tài xế, hệ thống sẽ tiếp tục khóa nguồn lực theo quy tắc BR-09, ngăn cản các chuyến hàng tiếp theo vận hành.

**Independent Test**: Có thể kiểm thử độc lập trên chuyến hàng ở trạng thái `DELIVERED` đã có bằng chứng bàn giao và không có phụ phí chờ duyệt: xác nhận hoàn tất với thời điểm giải phóng hợp lệ; kiểm tra trạng thái chuyển sang `COMPLETED`, lịch chiếm dụng của xe và tài xế kết thúc, và xe/tài xế có thể được phân công nhận hàng ngay cho chuyến mới.

**Acceptance Scenarios**:

1. **Given** chuyến hàng đang ở trạng thái `DELIVERED`, có đầy đủ tệp bằng chứng và không có phụ phí nào đang chờ duyệt (`PENDING`), **When** điều phối viên xác nhận hoàn tất với thời điểm giải phóng xe/tài xế hợp lệ ($\ge$ thời điểm giao hàng và $\le$ thời điểm hiện tại), **Then** chuyến hàng chuyển sang trạng thái `COMPLETED`, hệ thống cập nhật lịch chiếm dụng của xe tải và tài xế thành đã hoàn thành (giải phóng nguồn lực), và ghi nhận sự kiện hoàn tất vào dòng thời gian.
2. **Given** chuyến hàng đang ở `DELIVERED`, **When** điều phối viên nhập thời điểm giải phóng nguồn lực trước thời điểm giao hàng hoặc ở tương lai so với thời điểm thao tác, **Then** hệ thống từ chối hoàn tất và yêu cầu nhập mốc thời gian hợp lệ.
3. **Given** chuyến hàng chưa ở trạng thái `DELIVERED` (ví dụ đang ở `IN_TRANSIT` hoặc `ASSIGNED`), **When** điều phối viên cố gắng bấm chốt hoàn tất, **Then** hệ thống chặn thao tác để ngăn chặn nhảy cóc quy trình.
4. **Given** chuyến hàng đang ở `DELIVERED` nhưng có phụ phí phát sinh đang ở trạng thái chờ duyệt (`PENDING`), **When** điều phối viên thực hiện hoàn tất, **Then** hệ thống cảnh báo yêu cầu xử lý dứt điểm phụ phí trước khi đóng chuyến.

---

### User Story 3 - Xử lý Giao hàng Không Thành công & Ghi nhận Sự cố (Priority: P2)

Là điều phối viên, tôi muốn ghi nhận trường hợp giao hàng thất bại (khách từ chối nhận, sai địa chỉ, người nhận không liên lạc được, hàng hóa bị hư hại trên đường) mà không làm chuyến hàng bị chuyển sai thành `DELIVERED`, đồng thời ghi nhận sự cố để các bên liên quan cùng phối hợp xử lý.

**Why this priority**: Thực tế vận tải luôn có rủi ro giao hàng không thành công; hệ thống phải phản ánh trung thực thực tế, giữ nguyên chuyến ở `IN_TRANSIT` và lập biên bản sự cố thay vì ép chuyển sang đã giao.

**Independent Test**: Có thể kiểm thử độc lập bằng cách chọn kết quả "Giao không thành công" (`FAILED`), nhập nguyên nhân sự cố, mô tả chi tiết và người thông báo; kiểm tra chuyến vẫn giữ nguyên trạng thái `IN_TRANSIT`, một bản ghi sự cố mới được khởi tạo và ghi vào nhật ký sự cố của chuyến.

**Acceptance Scenarios**:

1. **Given** chuyến hàng đang ở `IN_TRANSIT`, **When** điều phối viên ghi nhận kết quả giao hàng thất bại (`FAILED`) kèm phân loại nguyên nhân và mô tả chi tiết, **Then** chuyến hàng giữ nguyên trạng thái `IN_TRANSIT` (không chuyển sang `DELIVERED`), và một bản ghi sự cố vận chuyển được tạo lập gắn liền với mã chuyến hàng.
2. **Given** chuyến hàng có sự cố giao hàng thất bại đang dở dang, **When** người dùng cố gắng thực hiện hành động hoàn tất chuyến hàng, **Then** hệ thống không cho phép hoàn tất chuyến hàng khi chưa đạt mốc `DELIVERED`.
3. **Given** sự cố giao hàng được ghi nhận, **When** điều phối viên hoặc quản lý xem thông tin chuyến hàng, **Then** nhật ký sự cố hiển thị nổi bật cảnh báo về sự cố đang chờ xử lý cùng lịch sử biên bản.

---

### User Story 4 - Quản lý và Tra cứu Tệp Bằng chứng Bàn giao POD (Priority: P2)

Là nhân viên điều phối, kinh doanh hoặc quản lý, tôi muốn xem danh sách các tệp bằng chứng bàn giao (tên tệp, loại chứng từ, dung lượng, người tải lên, thời điểm tải) và tải xuống hoặc xem trực tiếp tệp, để đối chiếu thông tin giao nhận khi khách hàng thắc mắc hoặc kế toán kiểm toán.

**Why this priority**: Chứng từ bàn giao (biên bản giao hàng có chữ ký, ảnh chụp kiện hàng tại kho nhận) là tài liệu pháp lý quan trọng nhất của dịch vụ vận tải hàng hóa.

**Independent Test**: Có thể kiểm thử độc lập bằng cách tải lên tệp hợp lệ (ảnh PNG hoặc tệp PDF dưới 10MB), kiểm tra tệp xuất hiện trong danh sách bằng chứng trên màn hình chi tiết chuyến, có thể mở xem trực tiếp hoặc tải về nội dung nguyên vẹn; kiểm tra tải lên tệp sai định dạng (ví dụ `.exe`, `.txt`) hoặc tệp rỗng bị hệ thống từ chối.

**Acceptance Scenarios**:

1. **Given** chuyến hàng đã có tệp bằng chứng được tải lên, **When** người dùng truy cập màn hình chi tiết chuyến hàng, **Then** khu vực bằng chứng giao nhận hiển thị danh sách các tệp với biểu tượng trực quan, dung lượng định dạng dễ đọc, thời điểm tải lên và liên kết xem/tải về.
2. **Given** người dùng chọn tệp tải lên có định dạng không được hỗ trợ (không thuộc nhóm PDF, JPG, JPEG, PNG) hoặc vượt quá giới hạn dung lượng quy định (10 MB), **Then** hệ thống từ chối tiếp nhận tệp và hiển thị thông báo lỗi giải thích rõ ràng định dạng và kích thước cho phép.
3. **Given** chuyến hàng đã ở trạng thái `DELIVERED`, **When** điều phối viên cần bổ sung thêm chứng từ phụ (ví dụ phiếu cân lại, biên bản bổ sung), **Then** hệ thống vẫn cho phép tải bổ sung tệp bằng chứng vào danh mục chứng từ của chuyến trước khi chuyến được chốt hoàn tất.

---

### User Story 5 - Dòng thời gian Lịch sử Toàn diện & Phân quyền Truy cập (Priority: P3)

Là người dùng hệ thống (DSP, SAL, MGR), tôi muốn theo dõi toàn bộ hành trình chuyến hàng trên dòng thời gian từ lúc tạo đơn, nhận hàng, xuất bến, giao hàng đến hoàn tất (và các sự cố nếu có); đồng thời chỉ vai trò Điều phối viên (DSP) mới được quyền thực hiện giao hàng và hoàn tất, các vai trò khác chỉ có quyền tra cứu.

**Why this priority**: Đảm bảo tính minh bạch, khả năng giải trình (Audit Trail) và bảo mật phân quyền theo nguyên tắc phân công trách nhiệm trong doanh nghiệp vận tải.

**Independent Test**: Có thể kiểm thử độc lập bằng cách đăng nhập bằng tài khoản kinh doanh (`SAL`) hoặc quản lý (`MGR`), kiểm tra họ xem được đầy đủ dòng thời gian và các mốc giao hàng/hoàn tất, nhưng các nút thao tác xác nhận giao hàng và hoàn tất bị ẩn hoặc trả về lỗi 403 Forbidden nếu cố tình gửi yêu cầu.

**Acceptance Scenarios**:

1. **Given** người dùng có vai trò Kinh doanh (`SAL`) hoặc Quản lý (`MGR`), **When** xem chi tiết chuyến hàng, **Then** toàn bộ thông tin mốc giao hàng, thông tin người nhận, bằng chứng và dòng thời gian hiển thị đầy đủ ở chế độ chỉ đọc (Read-only); không hiển thị nút thực thi thao tác giao hàng hoặc hoàn tất.
2. **Given** người dùng vai trò `SAL` hoặc `MGR`, **When** cố tình gửi yêu cầu cập nhật giao hàng hoặc hoàn tất qua đường dẫn thao tác, **Then** hệ thống từ chối và báo lỗi không có quyền truy cập.
3. **Given** chuyến hàng đã đi qua toàn bộ vòng đời, **When** xem dòng thời gian các mốc, **Then** các sự kiện hiển thị đúng thứ tự thời gian logic: `UNASSIGNED` ➔ `ASSIGNED` ➔ `PICKED_UP` ➔ `IN_TRANSIT` ➔ `DELIVERED` ➔ `COMPLETED`, kèm thông tin người thực hiện và sự sai khác (nếu có) giữa thời điểm thực tế và thời điểm ghi nhận.

---

### Edge Cases

- **Mất kết nối mạng giữa lúc tải tệp**: Tệp bằng chứng tải lên bị đứt quãng giữa chừng không được tạo bản ghi rác trong cơ sở dữ liệu; giao dịch ghi nhận giao hàng bị hủy hoàn toàn và giữ nguyên trạng thái `IN_TRANSIT`.
- **Giao hàng ngay tại điểm lấy hoặc kho kế cận**: Thời điểm giao hàng thực tế trùng khít với thời điểm nhận hàng (`actual_delivery_time == actual_pickup_time`). Hệ thống chấp nhận nếu thời gian bằng nhau, chỉ từ chối khi thời điểm giao hàng xảy ra trước thời điểm nhận hàng.
- **Nhiều tệp bằng chứng được nộp đồng thời**: Điều phối viên tải lên cùng lúc 3 ảnh chụp và 1 tệp PDF biên bản; hệ thống tiếp nhận toàn bộ các tệp hợp lệ và hiển thị đầy đủ trong danh sách bằng chứng của chuyến.
- **Xe tải và tài xế tiếp tục nhận chuyến tiếp theo**: Sau khi chuyến hiện tại được chốt `COMPLETED`, hệ thống giải phóng lịch chiếm dụng ngay lập tức; khi điều phối viên tiến hành ghi nhận nhận hàng cho chuyến tiếp theo của cùng xe tải/tài xế đó, hệ thống không báo lỗi vi phạm bận việc theo quy tắc BR-09.
- **Tệp bằng chứng trùng tên**: Khi điều phối viên tải lên tệp có tên trùng với tệp đã có trong hệ thống, hệ thống tự động đổi tên định danh duy nhất để tránh ghi đè dữ liệu tệp cũ.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống BẮT BUỘC chỉ cho phép thực hiện xác nhận giao hàng khi chuyến hàng đang ở trạng thái `IN_TRANSIT`. Tuyệt đối không cho phép xác nhận giao hàng khi chuyến ở trạng thái `UNASSIGNED`, `ASSIGNED`, hoặc `PICKED_UP`.
- **FR-002**: Khi ghi nhận giao hàng thành công, hệ thống BẮT BUỘC thu thập:
  - Thời điểm giao hàng thực tế (`actual_delivery_time`).
  - Họ tên người nhận hàng (`recipient_name`).
  - Kết quả giao hàng: Thành công (`SUCCESS`).
  - Ghi chú giao hàng (tùy chọn).
  - Ít nhất một tệp bằng chứng bàn giao (Proof of Delivery - POD).
- **FR-003**: Thời điểm giao hàng thực tế BẮT BUỘC phải lớn hơn hoặc bằng thời điểm nhận hàng thực tế (`actual_delivery_time >= actual_pickup_time`).
- **FR-004**: Tệp bằng chứng bàn giao BẮT BUỘC phải thuộc các định dạng cho phép: PDF, JPG, JPEG, PNG với dung lượng tối đa không vượt quá 10 MB cho mỗi tệp.
- **FR-005**: Khi ghi nhận kết quả giao hàng không thành công (`FAILED`), hệ thống BẮT BUỘC:
  - Giữ nguyên trạng thái chuyến hàng ở `IN_TRANSIT` (không được chuyển sang `DELIVERED`).
  - Bắt buộc thu thập lý do thất bại, người báo cáo và mô tả sự cố để tạo một bản ghi sự cố gắn liền với chuyến hàng.
- **FR-006**: Chuyển trạng thái sang Hoàn tất (`COMPLETED`) CHỈ ĐƯỢC PHÉP khi:
  - Chuyến hàng đang ở trạng thái `DELIVERED`.
  - Chuyến hàng đã có ít nhất một tệp bằng chứng giao hàng hợp lệ.
  - Không có khoản phụ phí phát sinh nào đang ở trạng thái chờ duyệt (`PENDING`).
- **FR-007**: Khi hoàn tất chuyến hàng, hệ thống BẮT BUỘC lưu trữ thời điểm xe tải và tài xế thực sự được giải phóng (`actual_completed_time`):
  - Mốc thời gian này BẮT BUỘC không được trước thời điểm giao hàng thực tế (`actual_completed_time >= actual_delivery_time`).
  - Mốc thời gian này BẮT BUỘC không được nằm ở tương lai so với thời điểm hệ thống ghi nhận (`actual_completed_time <= current_time`).
- **FR-008**: Khi một chuyến hàng chuyển sang `COMPLETED`, hệ thống BẮT BUỘC tự động chuyển trạng thái các lịch chiếm dụng tương ứng của Xe tải và Tài xế từ `IN_PROGRESS` sang `COMPLETED`, chính thức giải phóng nguồn lực để phục vụ các chuyến hàng kế tiếp theo quy tắc BR-09.
- **FR-009**: Hệ thống BẮT BUỘC ghi nhận mọi sự kiện chuyển đổi trạng thái (`DELIVERED`, `COMPLETED`) và biên bản sự cố vào bảng dòng thời gian sự kiện bất biến (`TripEvent`), ghi nhận đồng thời thời điểm diễn ra thực tế (`actual_time`), thời điểm hệ thống lưu vết (`recorded_at`), và định danh người dùng thực hiện.
- **FR-010**: Phân quyền truy cập theo vai trò người dùng (RBAC):
  - Vai trò Điều phối viên (`DSP`): Được toàn quyền ghi nhận giao hàng, tải bằng chứng, báo cáo sự cố và hoàn tất chuyến hàng.
  - Vai trò Kinh doanh (`SAL`) và Quản lý (`MGR`): Chỉ có quyền tra cứu thông tin chi tiết, xem dòng thời gian và xem/tải bằng chứng (Read-only); hệ thống từ chối mọi thao tác ghi nhận với mã lỗi 403 Forbidden.

---

### Key Entities *(include if feature involves data)*

- **Chuyến hàng (Trip)**: Thực thể trung tâm lưu trữ thông tin đơn vận chuyển, trạng thái vận hành (`IN_TRANSIT`, `DELIVERED`, `COMPLETED`), thời điểm giao thực tế (`actual_delivery_time`), người nhận hàng (`recipient_name`), thời điểm hoàn tất giải phóng xe/tài xế (`actual_completed_time`), thời điểm hệ thống ghi nhận giao hàng (`delivery_recorded_at`) và thời điểm hệ thống ghi nhận hoàn tất (`completed_recorded_at`).
- **Bằng chứng giao nhận (TripEvidence / POD)**: Bản ghi liên kết với chuyến hàng, lưu trữ đường dẫn tệp tài liệu bằng chứng, tên tệp gốc, loại nội dung (MIME type), dung lượng tệp, phân loại chứng từ (ví dụ `POD`, `WEIGHING_SLIP`, `INCIDENT_PHOTO`), người tải lên và thời điểm tải lên.
- **Sự kiện chuyến hàng (TripEvent)**: Bản ghi nhật ký bất biến ghi nhận mỗi bước chuyển trạng thái (từ `IN_TRANSIT` sang `DELIVERED`, từ `DELIVERED` sang `COMPLETED`), lưu trữ mốc thời gian thực tế, mốc thời gian hệ thống và người thực hiện.
- **Sự cố chuyến hàng (TripIssue / Incident)**: Bản ghi ghi nhận các vấn đề bất thường trong quá trình giao nhận (ví dụ giao hàng thất bại, hàng hư hỏng, trễ hạn giao), lưu mã sự cố, loại sự cố, mô tả, người tạo và trạng thái xử lý.
- **Lịch chiếm dụng nguồn lực (ResourceBooking)**: Bản ghi theo dõi trạng thái sử dụng của Xe tải và Tài xế, chuyển từ `IN_PROGRESS` sang `COMPLETED` ngay khi chuyến hàng hoàn tất.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các chuyến hàng khi chuyển sang trạng thái `DELIVERED` đều có đầy đủ thông tin người nhận hàng và ít nhất một tệp bằng chứng giao nhận (POD) hợp lệ.
- **SC-002**: 100% các chuyến hàng khi chuyển sang trạng thái `COMPLETED` đều giải phóng xe tải và tài xế lập tức, cho phép các nguồn lực này thực hiện ngay các chuyến hàng tiếp theo mà không bị từ chối bởi lỗi bận việc BR-09.
- **SC-003**: 0% vi phạm toàn vẹn luồng trạng thái vận hành: không có bất kỳ chuyến hàng nào chuyển thẳng từ `IN_TRANSIT` sang `COMPLETED` mà bỏ qua bước `DELIVERED`, và không có chuyến nào ở trạng thái khác `IN_TRANSIT` được phép ghi nhận `DELIVERED`.
- **SC-004**: Thời gian thực hiện thao tác tải tệp bằng chứng và xác nhận giao hàng trên giao diện web hoàn tất trong dưới 60 giây đối với người dùng điều phối.
- **SC-005**: 100% các trường hợp giao hàng không thành công đều giữ nguyên trạng thái `IN_TRANSIT` và được tạo lập bản ghi sự cố có thể truy vết.
- **SC-006**: 100% các yêu cầu ghi nhận giao hàng hoặc hoàn tất gửi từ tài khoản không mang vai trò `DSP` đều bị hệ thống chặn với mã phản hồi từ chối quyền truy cập (403 Forbidden).

---

## Assumptions

- **Lưu trữ tệp chứng từ**: Hệ thống triển khai lưu trữ tệp cục bộ an toàn trong thư mục máy chủ (ví dụ `uploads/evidence/`) với định danh tên tệp ngẫu nhiên chống trùng lặp; việc tích hợp lưu trữ đám mây (S3, Cloud Storage) là phần mở rộng nâng cấp trong tương lai nếu có yêu cầu.
- **Phụ phí phát sinh**: Ở phiên bản hiện tại, phụ phí phát sinh (nếu có) được kiểm tra dựa trên các khoản phụ phí gắn với chuyến hàng; nếu chuyến không có phụ phí hoặc các phụ phí đã ở trạng thái đã duyệt/đã hủy thì đủ điều kiện hoàn tất.
- **Môi trường kết nối của tài xế**: Tài xế liên lạc với điều phối viên qua điện thoại/ứng dụng chat để gửi ảnh biên bản giao hàng và thông tin người nhận; điều phối viên là người trực tiếp thao tác nhập liệu và tải ảnh lên hệ thống Freight ERP.
- **Xác thực và phân quyền**: Tái sử dụng cơ chế phiên đăng nhập bảo mật (Session-based Cookie Auth) và phân quyền vai trò (`DSP`, `SAL`, `MGR`) đã được thiết lập từ các module trước.
