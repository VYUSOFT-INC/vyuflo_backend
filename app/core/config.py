"""
Application settings loaded from environment variables.

Rules:
- Fields WITH    = "..." → optional, use default if missing from .env
- Fields WITHOUT = "..." → REQUIRED, app crashes at startup if missing
- Only SECRET_KEY, LOCAL_DATABASE_URL, FRONTEND_URL are truly required
"""
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME:    str  = "VisaFlow"
    APP_VERSION: str  = "1.0.0"
    APP_ENV:     str  = "development"   # development | staging | production
    DEBUG:       bool = False

    # REQUIRED — no default. App crashes loudly if missing (better than silent insecurity)
    SECRET_KEY: str

    # ── AI ────────────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""

    # ── Database ──────────────────────────────────────────────────────────────
    LOCAL_DATABASE_URL: str          # REQUIRED
    ZOHO_DATABASE_URL:  str = ""     # optional — only used when DATABASE_ENV=zoho
    DATABASE_ENV:       str = "local"  # "local" | "zoho"

    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_ENV == "zoho":
            return self.ZOHO_DATABASE_URL
        return self.LOCAL_DATABASE_URL

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ───────────────────────────────────────────────────────────────────
    ALGORITHM:                   str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS:   int = 7

    # ── AWS S3 (optional — only used when STORAGE_BACKEND=s3) ────────────────
    AWS_ACCESS_KEY_ID:     str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION:            str = ""
    S3_BUCKET:             str = ""
    STORAGE_BACKEND:       str = "local"  # "local" | "s3"

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = []
    COOKIE_SECURE: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    # ── OAuth (all optional) ──────────────────────────────────────────────────
    GOOGLE_CLIENT_ID:        str = ""
    GOOGLE_CLIENT_SECRET:    str = ""
    MICROSOFT_CLIENT_ID:     str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    APPLE_CLIENT_ID:         str = ""

    # LinkedIn
    LINKEDIN_CLIENT_ID:     str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_REDIRECT_URI:  str = ""

    # ── Email ─────────────────────────────────────────────────────────────────
    SMTP_USERNAME:   str  = ""
    SMTP_PASSWORD:   str  = ""
    SMTP_FROM_EMAIL: str  = "noreply@visaflow.com"
    SMTP_PORT:       int  = 587
    SMTP_HOST:       str  = "smtp.gmail.com"
    MAIL_STARTTLS:   bool = True
    MAIL_SSL_TLS:    bool = False

    # ── Stripe ────────────────────────────────────────────────────────────────
    STRIPE_SECRET_KEY:     str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # ── SMS / Twilio (optional) ───────────────────────────────────────────────
    TWILIO_ACCOUNT_SID:  str = ""
    TWILIO_AUTH_TOKEN:   str = ""
    TWILIO_FROM_NUMBER:  str = ""

    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── OTP ───────────────────────────────────────────────────────────────────
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS:   int = 5

    # ── Zoho (all optional) ───────────────────────────────────────────────────
    ZOHO_CLIENT_ID:     str = ""
    ZOHO_CLIENT_SECRET: str = ""
    ZOHO_REFRESH_TOKEN: str = ""
    ZOHO_ORG_ID:        str = ""
    ZOHO_WORKSPACE_ID:  str = ""

    # ── Frontend ──────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"


settings = Settings()