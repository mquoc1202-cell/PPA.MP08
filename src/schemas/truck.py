from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from src.models.truck import TruckStatus

class CreateTruckRequest(BaseModel):
    plate_number: str = Field(..., min_length=5, max_length=20, description="Biển số xe hiển thị gốc, ví dụ: 29C-123.45")
    truck_type: str = Field(..., min_length=2, max_length=50, description="Loại xe, ví dụ: Xe thùng kín 5T")
    capacity_kg: int = Field(..., gt=0, description="Tải trọng tối đa tính bằng kg (> 0)")
    description: Optional[str] = Field(None, max_length=255, description="Mô tả bổ sung")

    @field_validator("plate_number")
    @classmethod
    def validate_plate(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Biển số xe không được để trống")
        return clean

class UpdateTruckRequest(BaseModel):
    plate_number: str = Field(..., min_length=5, max_length=20)
    truck_type: str = Field(..., min_length=2, max_length=50)
    capacity_kg: int = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=255)

class ChangeTruckStatusRequest(BaseModel):
    status: TruckStatus
    reason: Optional[str] = None

class TruckDetailResponse(BaseModel):
    id: int
    plate_number: str
    normalized_plate: str
    truck_type: str
    capacity_kg: int
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
