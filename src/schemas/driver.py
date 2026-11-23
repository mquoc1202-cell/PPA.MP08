import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from src.models.driver import DriverStatus

class CreateDriverRequest(BaseModel):
    driver_code: str = Field(..., min_length=2, max_length=20, description="Mã tài xế duy nhất, ví dụ: TX001")
    full_name: str = Field(..., min_length=2, max_length=100, description="Họ và tên đầy đủ")
    phone_number: str = Field(..., min_length=9, max_length=20, description="Số điện thoại liên hệ")

    @field_validator("driver_code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        clean = v.strip().upper()
        if not clean:
            raise ValueError("Mã tài xế không được để trống")
        return clean

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean = re.sub(r"[^0-9+]", "", v.strip())
        if len(clean) < 9 or len(clean) > 15:
            raise ValueError("Số điện thoại không hợp lệ (cần từ 9 đến 15 chữ số)")
        return clean

class UpdateDriverRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=9, max_length=20)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean = re.sub(r"[^0-9+]", "", v.strip())
        if len(clean) < 9 or len(clean) > 15:
            raise ValueError("Số điện thoại không hợp lệ")
        return clean

class ChangeDriverStatusRequest(BaseModel):
    status: DriverStatus
    reason: Optional[str] = None

class DriverDetailResponse(BaseModel):
    id: int
    driver_code: str
    full_name: str
    phone_number: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
