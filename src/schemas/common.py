from typing import Generic, TypeVar, Optional, Any, Dict
from pydantic import BaseModel, Field

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    """Standardized API Response Envelope per AGENTS.md rules."""
    success: bool = True
    data: Optional[T] = None
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict)
