from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CreateTripRequest(BaseModel):
    sender_name: str = Field(..., min_length=2, max_length=100, description="Họ tên người gửi")
    sender_phone: str = Field(..., min_length=8, max_length=20, description="Số điện thoại người gửi")
    pickup_address: str = Field(..., min_length=3, max_length=255, description="Địa chỉ nhận hàng")
    delivery_address: str = Field(..., min_length=3, max_length=255, description="Địa chỉ giao hàng")
    cargo_weight_kg: int = Field(..., gt=0, description="Khối lượng hàng hóa (kg)")
    cargo_type: str = Field(..., min_length=2, max_length=100, description="Loại hàng hóa")
    notes: Optional[str] = Field(None, max_length=500, description="Ghi chú điều phối")


class AssignTripRequest(BaseModel):
    truck_id: int = Field(..., description="ID xe tải được gán")
    driver_id: int = Field(..., description="ID tài xế được gán")
    start_time: datetime = Field(..., description="Thời điểm bắt đầu dự kiến")
    end_time: datetime = Field(..., description="Thời điểm kết thúc dự kiến")


class ReassignTripRequest(BaseModel):
    truck_id: int = Field(..., description="ID xe tải mới")
    driver_id: int = Field(..., description="ID tài xế mới")
    start_time: Optional[datetime] = Field(None, description="Thời điểm bắt đầu mới (nếu thay đổi)")
    end_time: Optional[datetime] = Field(None, description="Thời điểm kết thúc mới (nếu thay đổi)")


class TripItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_code: str
    sender_name: str
    sender_phone: str
    pickup_address: str
    delivery_address: str
    cargo_weight_kg: int
    cargo_type: str
    estimated_start_time: Optional[datetime] = None
    estimated_end_time: Optional[datetime] = None
    status: str
    assigned_truck_id: Optional[int] = None
    assigned_driver_id: Optional[int] = None
    actual_cargo_weight_kg: Optional[int] = None
    handover_person: Optional[str] = None
    cargo_condition: Optional[str] = None
    discrepancy_notes: Optional[str] = None
    actual_pickup_time: Optional[datetime] = None
    actual_depart_time: Optional[datetime] = None
    pickup_recorded_at: Optional[datetime] = None
    depart_recorded_at: Optional[datetime] = None
    actual_delivery_time: Optional[datetime] = None
    actual_completed_time: Optional[datetime] = None
    recipient_name: Optional[str] = None
    delivery_notes: Optional[str] = None
    delivery_recorded_at: Optional[datetime] = None
    completed_recorded_at: Optional[datetime] = None
    is_delayed: bool = False
    has_open_issues: bool = False
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RecordPickupRequest(BaseModel):
    actual_pickup_time: datetime = Field(..., description="Thời điểm nhận hàng thực tế")
    handover_person: str = Field(..., min_length=2, max_length=100, description="Người bàn giao hàng phía kho")
    actual_cargo_weight_kg: int = Field(..., gt=0, description="Khối lượng hàng thực tế cân được (kg)")
    cargo_condition: str = Field(default="Nguyên đai nguyên kiện", max_length=255, description="Tình trạng quy cách, bao bì")
    discrepancy_notes: Optional[str] = Field(None, max_length=500, description="Ghi chú chênh lệch nếu có")


class RecordDepartureRequest(BaseModel):
    actual_depart_time: datetime = Field(..., description="Thời điểm xe bắt đầu lăn bánh")
    notes: Optional[str] = Field(None, max_length=500, description="Ghi chú xuất phát")


class RecordDeliveryRequest(BaseModel):
    actual_delivery_time: datetime = Field(..., description="Thời điểm giao hàng thực tế")
    recipient_name: Optional[str] = Field(None, max_length=100, description="Họ tên người nhận hàng")
    result: str = Field(default="SUCCESS", description="Kết quả giao hàng (SUCCESS / FAILED)")
    delivery_notes: Optional[str] = Field(None, max_length=500, description="Ghi chú giao hàng hoặc lý do thất bại")


class CompleteTripRequest(BaseModel):
    actual_completed_time: datetime = Field(..., description="Thời điểm xe và tài xế thực sự được giải phóng")
    notes: Optional[str] = Field(None, max_length=500, description="Ghi chú hoàn tất")


class TripEvidenceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: int
    file_name: str
    file_size_bytes: int
    mime_type: str
    evidence_type: str
    notes: Optional[str] = None
    download_url: Optional[str] = None
    created_at: datetime


class TripIssueItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: int
    issue_type: str
    description: str
    status: str
    occurred_at: Optional[datetime] = None
    handled_by: Optional[str] = None
    estimated_resolution_time: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    reported_by_user_id: Optional[int] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class CreateTripIssueRequest(BaseModel):
    issue_type: str = Field(..., description="Phân loại sự cố")
    description: str = Field(..., min_length=5, max_length=1000, description="Mô tả sự cố")
    occurred_at: Optional[datetime] = Field(None, description="Thời điểm phát sinh sự cố")
    handled_by: Optional[str] = Field(None, max_length=150, description="Người/đơn vị phụ trách xử lý")
    estimated_resolution_time: Optional[datetime] = Field(None, description="Thời gian dự kiến khắc phục")


class ResolveTripIssueRequest(BaseModel):
    resolution_notes: str = Field(..., min_length=5, max_length=1000, description="Kết quả giải quyết sự cố")


class RescheduleTripRequest(BaseModel):
    new_estimated_end_time: datetime = Field(..., description="Thời điểm kết thúc dự kiến mới")
    reason: Optional[str] = Field(None, max_length=500, description="Lý do gia hạn")


class ConflictBookingItem(BaseModel):
    trip_id: Optional[int] = None
    reference_code: str
    service_type: str = "FREIGHT"
    resource_type: str
    resource_name: Optional[str] = None
    start_time: datetime
    end_time: datetime


class TripIssuesListResponse(BaseModel):
    success: bool = True
    data: List[TripIssueItem] = Field(default_factory=list)
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class TripIssueDetailResponse(BaseModel):
    success: bool = True
    data: Optional[TripIssueItem] = None
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class RescheduleSuccessResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class RescheduleConflictResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any] = Field(default_factory=dict)
    error: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class TripEvidenceResponse(BaseModel):
    success: bool = True
    data: List[TripEvidenceItem] = Field(default_factory=list)
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class TripEventItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: int
    event_type: str
    from_status: str
    to_status: str
    actual_time: datetime
    recorded_at: datetime
    recorded_by_user_id: Optional[int] = None
    notes: Optional[str] = None


class TripEventsResponse(BaseModel):
    success: bool = True
    data: List[TripEventItem] = Field(default_factory=list)
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class TripDetailResponse(BaseModel):
    success: bool = True
    data: Optional[TripItem] = None
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class TripListResponse(BaseModel):
    success: bool = True
    data: List[TripItem] = Field(default_factory=list)
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class BookingItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resource_type: str
    resource_id: int
    reference_code: str
    service_type: str = "FREIGHT"
    start_time: datetime
    end_time: datetime
    status: str


class ScheduleListResponse(BaseModel):
    success: bool = True
    data: List[BookingItem] = Field(default_factory=list)
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class ConflictResponse(BaseModel):
    success: bool = False
    data: Dict[str, Any] = Field(default_factory=dict)
    error: str = "Xe hoặc tài xế đã bị chiếm dụng trong khoảng thời gian này."
    meta: Dict[str, Any] = Field(default_factory=dict)
