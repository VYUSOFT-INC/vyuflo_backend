"""
Custom ASGI middlewares.
"""
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.redis import redis_increment

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple IP-based rate limiting using Redis counters.
    Only applied to /api/v1/auth/* endpoints.
    """
    AUTH_PATHS = {"/api/v1/auth/login", "/api/v1/auth/signup"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.AUTH_PATHS:
            ip = request.client.host if request.client else "unknown"
            key = f"rate_limit:{ip}:{request.url.path}"
            try:
                count = await redis_increment(key, expire_seconds=60)
                if count > settings.RATE_LIMIT_PER_MINUTE:
                    return Response(
                        content='{"detail":"Too many requests"}',
                        status_code=429,
                        media_type="application/json",
                    )
            except Exception:
                # Redis unavailable → allow request through
                pass
        return await call_next(request)