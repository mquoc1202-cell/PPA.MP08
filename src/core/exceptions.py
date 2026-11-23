from typing import Any, List, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from src.core.logging import get_logger

logger = get_logger("exception_handler")

class DomainException(Exception):
    """Base class for all domain-level exceptions."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class EntityNotFoundError(DomainException):
    """Raised when an entity is not found in repository."""
    pass

class BusinessRuleViolationError(DomainException):
    """Raised when a business rule constraint is violated."""
    pass

class ConflictError(DomainException):
    """Raised when an operation conflicts with existing state."""
    pass

class ScheduleConflictError(ConflictError):
    """Raised when an operation conflicts with future or in-progress bookings."""
    def __init__(self, message: str, conflicting_bookings: Optional[List[dict]] = None):
        super().__init__(message)
        self.conflicting_bookings = conflicting_bookings or []

def register_exception_handlers(app: FastAPI) -> None:
    """Registers centralized exception handlers to guarantee masked errors and standard JSON response."""

    @app.exception_handler(EntityNotFoundError)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundError):
        logger.warning(f"Entity not found: {exc.message} on path {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "data": None,
                "error": exc.message,
                "meta": {}
            }
        )

    @app.exception_handler(ScheduleConflictError)
    async def schedule_conflict_handler(request: Request, exc: ScheduleConflictError):
        logger.warning(f"Schedule conflict on {request.url.path}: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "data": {
                    "conflicting_bookings": exc.conflicting_bookings
                },
                "error": exc.message,
                "meta": {}
            }
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        logger.warning(f"Conflict on {request.url.path}: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "data": None,
                "error": exc.message,
                "meta": {}
            }
        )

    @app.exception_handler(BusinessRuleViolationError)
    async def business_rule_handler(request: Request, exc: BusinessRuleViolationError):
        logger.warning(f"Business rule violation on {request.url.path}: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "data": None,
                "error": exc.message,
                "meta": {}
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        first_error = exc.errors()[0] if exc.errors() else {}
        loc = " -> ".join(str(l) for l in first_error.get("loc", []))
        msg = first_error.get("msg", "Dữ liệu yêu cầu không hợp lệ.")
        error_detail = f"{loc}: {msg}" if loc else msg
        logger.warning(f"Validation error on {request.url.path}: {error_detail}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "data": {"validation_errors": exc.errors()},
                "error": error_detail,
                "meta": {}
            }
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled server error on {request.url.path}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "data": None,
                "error": "Có lỗi xảy ra, vui lòng thử lại sau.",
                "meta": {}
            }
        )
