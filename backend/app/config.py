from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Kanakku (கணக்கு)"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Canonical Database: PostgreSQL 16+
    # In development/test, can be overridden via DATABASE_URL or fallback to local SQLite for offline tests
    DATABASE_URL: str = "postgresql+psycopg://kanakku:kanakku_secret_123@localhost:5432/kanakku_prod"
    SQLITE_DEV_FALLBACK_URL: str = "sqlite:///./kanakku_dev.db"
    ALLOW_SQLITE_FALLBACK: bool = True

    # Security & JWT Tokens
    SECRET_KEY: str = "kanakku_super_secret_dev_key_change_in_production_32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # Phone Authentication & Defensive Rate Limiting
    DEFAULT_PHONE_COUNTRY_CODE: str = "+91"
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Currency Defaults
    DEFAULT_CURRENCY: str = "INR"
    DEFAULT_CURRENCY_SYMBOL: str = "₹"

    # CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
