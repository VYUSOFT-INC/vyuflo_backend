"""
Custom application exceptions and a registration helper for FastAPI.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base class for all application-level errors."""
    status_code: int = 500
    default_message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class BadRequestException(AppException):
    status_code = 400
    default_message = "Bad request"


class UnauthorizedException(AppException):
    status_code = 401
    default_message = "Authentication required"


class ForbiddenException(AppException):
    status_code = 403
    default_message = "Permission denied"


class NotFoundException(AppException):
    status_code = 404
    default_message = "Resource not found"


class ConflictException(AppException):
    status_code = 409
    default_message = "Resource already exists"


class UnprocessableException(AppException):
    status_code = 422
    default_message = "Validation error"


class TooManyRequestsException(AppException):
    status_code = 429
    default_message = "Too many requests"


# ── FastAPI registration ──────────────────────────────────────────────────────
def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )