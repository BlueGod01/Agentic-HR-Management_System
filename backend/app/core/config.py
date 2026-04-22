"""
Core configuration - loads from .env file via pydantic-settings
"""
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "Agentic AI HR System"
    APP_ENV: str = "development"
    APP_SECRET_KEY: str
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./hr_system.db"

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.DATABASE_URL

    @property
    def sync_database_url(self) -> str:
        """Sync URL for Alembic migrations"""
        url = self.DATABASE_URL
        if "postgresql+asyncpg" in url:
            return url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        if "sqlite+aiosqlite" in url:
            return url.replace("sqlite+aiosqlite", "sqlite")
        return url

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google Gemini
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-1.5-pro"
    GEMINI_TEMPERATURE: float = 0.2
    GEMINI_MAX_OUTPUT_TOKENS: int = 2048

    # WhatsApp (Green API)
    GREEN_API_INSTANCE_ID: str = ""
    GREEN_API_TOKEN: str = ""
    EMPLOYER_WHATSAPP_NUMBER: str = ""
    GREEN_API_BASE_URL: str = "https://api.green-api.com"

    # Email SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "HR System"
    SMTP_FROM_EMAIL: str = ""
    SMTP_TLS: bool = True

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Vector DB
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENV: Optional[str] = None
    PINECONE_INDEX_NAME: str = "hr-policies"

    # Alerts
    DAILY_ALERT_CRON: str = "0 18 * * *"
    HIGH_SEVERITY_ALERT_IMMEDIATE: bool = True
    VIOLATION_THRESHOLD_PER_USER: int = 3

    # Security
    BCRYPT_ROUNDS: int = 12
    RATE_LIMIT_PER_MINUTE: int = 60


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
