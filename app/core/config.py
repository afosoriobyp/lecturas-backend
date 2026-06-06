from __future__ import annotations

from typing import List

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # FastAPI
    APP_NAME: str = "Lectura Medidor API"
    APP_VERSION: str = "0.2.0"
    APP_DEBUG: bool = False
    API_PREFIX: str = ""

    # PostgreSQL async — sobrescribir vía .env
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = ""
    DATABASE_URL: PostgresDsn | str = ""

    # Pool tuning para entorno local
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_STATEMENT_TIMEOUT_MS: int = 10000

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str, info) -> str:
        if v and isinstance(v, str) and v.startswith("postgres"):
            # Render / Supabase usan postgres:// — convertir a postgresql+asyncpg://
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and "+asyncpg" not in v:
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            return v
        values = info.data
        user = values.get("POSTGRES_USER")
        password = values.get("POSTGRES_PASSWORD")
        db = values.get("POSTGRES_DB")
        if not user or not password or not db:
            return ""
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=user,
                password=password,
                host=values.get("POSTGRES_SERVER"),
                port=values.get("POSTGRES_PORT"),
                path=db,
            )
        )

    # CORS — usar ["*"] en dev, lista específica en producción
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://192.168.100.24:3000",
    ]

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

    # JWT — usando python-jose con cryptografia local
    JWT_SECRET_KEY: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_COOKIE_SECURE: bool = False  # False para dev local HTTP
    JWT_COOKIE_SAMESITE: str = "lax"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Uploads
    UPLOAD_DIR: str = "uploads"
    MAX_IMAGE_SIZE_MB: int = 5
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]
    MAX_FOTOS_PER_LECTURA: int = 5


settings = Settings()
