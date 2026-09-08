"""
PATCH for app/core/middlewares.py (or wherever RateLimitMiddleware lives)

Changes:
  1. FIXED gap: onboarding OTP paths (verify-email, resend-otp, verify-phone,
     resend-phone-otp) were not rate-limited at all. Added.
  2. Per-path limits instead of one global RATE_LIMIT_PER_MINUTE — signup
     and phone-otp-resend get stricter caps since they cost real money
     (SMS) or create real accounts.
  3. Logs when Redis is down and the limiter fails open, instead of
     silently swallowing it — you want to know if this safety net is
     actually working in production.

Add these two new settings to app/core/config.py (values below are a
starting point — tune after you see real traffic):

    RATE_LIMIT_PER_MINUTE: int = 10          # existing — general auth paths
    RATE_LIMIT_SIGNUP_PER_MINUTE: int = 3    # NEW — stricter, creates accounts
    RATE_LIMIT_OTP_PER_MINUTE: int = 5       # NEW — covers verify + resend (SMS cost)
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
    Redis-backed, IP + path rate limiting. Per-path limits reflect how
    expensive/abusable each endpoint is — signup creates a real account,
    phone OTP endpoints trigger a real SMS charge, so both get stricter
    caps than a plain login retry.

    NOTE — structural limit, not a bug: this is per-IP. A distributed,
    low-and-slow attacker (1 req/min spread across many IPs) is NOT
    stopped by any threshold here, at any window size. That gap needs
    CAPTCHA (blocks scripted/automated requests regardless of IP) or a
    provider-side fraud layer (e.g. Twilio Verify's built-in Fraud Guard,
    since you're already on Twilio) — not a tighter number in this file.
    """

    # path -> requests allowed per 60s window, per IP
    AUTH_PATHS: dict[str, int] = {
        "/api/v1/auth/login":                          10,
        "/api/v1/auth/signup":                          3,   # creates an account
        "/api/v1/auth/password-reset/request":          5,
        "/api/v1/auth/password-reset/verify-otp":       5,
        "/api/v1/auth/password-reset/complete":         5,
        # ── NEW — these had ZERO rate limiting before this patch ──────────
        "/api/v1/onboarding/verify-email":              5,   # brute-force guard
        "/api/v1/onboarding/resend-otp":                3,   # each resend = email + possible SMS
        "/api/v1/onboarding/verify-phone":              5,   # brute-force guard
        "/api/v1/onboarding/resend-phone-otp":          3,   # each resend = an SMS charge
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        limit = self.AUTH_PATHS.get(request.url.path)
        if limit is not None:
            ip = request.client.host if request.client else "unknown"
            key = f"rate_limit:{ip}:{request.url.path}"
            try:
                count = await redis_increment(key, expire_seconds=60)
                if count > limit:
                    logger.warning(
                        "rate_limit_exceeded",
                        ip=ip, path=request.url.path, count=count, limit=limit,
                    )
                    return Response(
                        content='{"detail":"Too many requests"}',
                        status_code=429,
                        media_type="application/json",
                    )
            except Exception as e:
                # Redis unavailable → fail OPEN (allow request through) —
                # unchanged behavior from your original, but now logged so
                # you notice if this safety net silently stops working.
                logger.warning("rate_limit_check_failed", path=request.url.path, error=str(e))
        return await call_next(request)