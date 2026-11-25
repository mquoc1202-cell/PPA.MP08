from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Tên đăng nhập")
    password: str = Field(..., min_length=1, description="Mật khẩu")


class UserSession(BaseModel):
    id: int
    username: str
    full_name: str
    role: str


class AuthResponse(BaseModel):
    success: bool = True
    data: Optional[UserSession] = None
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class UserProfileResponse(BaseModel):
    success: bool = True
    data: Optional[UserSession] = None
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class ActionResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
