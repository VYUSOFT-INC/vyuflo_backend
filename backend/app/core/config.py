"""
Application settings loaded from environment variables.
"""
from typing import List
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "VisaFlow"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "sai"

    ANTHROPIC_API_KEY : str
    
    # ── Database ──────────────────────────────────────────────────────────────
    # DATABASE_URL: str = "postgresql+asyncpg://postgres:Charan@localhost:5433/visaflow"
    
    LOCAL_DATABASE_URL: str
    ZOHO_DATABASE_URL: str
    DATABASE_ENV: str = "local"  # "local" or "zoho"
    DEBUG: bool = False

    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_ENV == "zoho":
            return self.ZOHO_DATABASE_URL
        return self.LOCAL_DATABASE_URL

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ───────────────────────────────────────────────────────────────────
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    COOKIE_SECURE: bool = True 

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    # ── OAuth ─────────────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    APPLE_CLIENT_ID: str = ""

    # ── Email ─────────────────────────────────────────────────────────────────
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@visaflow.com"
    SMTP_PORT: int = 587
    SMTP_HOST: str = "smtp.gmail.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False


    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── OTP ───────────────────────────────────────────────────────────────────
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5

    # Zoho
    ZOHO_CLIENT_ID: str
    ZOHO_CLIENT_SECRET: str
    ZOHO_REFRESH_TOKEN: str
    ZOHO_ORG_ID: str
    ZOHO_WORKSPACE_ID: str

settings = Settings()




