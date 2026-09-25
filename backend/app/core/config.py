import os
from typing import Any, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Carzinomax ERP"
    API_V1_STR: str = "/api/v1"

    # JWT & Auth
    # Required, sourced from .env. No default so the app refuses to start
    # with a well-known key (which would let anyone forge access tokens).
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Default admin user (seeded on startup) - required, sourced from .env
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str
    
    # Database
    # We allow ADMIN_DB_CONNECTION or DATABASE_URL
    DATABASE_URL: Optional[str] = None
    ADMIN_DB_CONNECTION: Optional[str] = None
    
    # Payroll/Paycheck calculation timespot (cron expression)
    PAYCHECK_CALCULATE_TIMESPOT: str = "0 0 1 * *"
    
    # Async database URL computed automatically
    ASYNC_DATABASE_URL: str = ""
    LLM_ORIGIN: str = ""
    LLM_TOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("ASYNC_DATABASE_URL", mode="before")
    @classmethod
    def assemble_async_db_connection(cls, v: Optional[str], info: Any) -> Any:
        """Assemble and compute the asynchronous database connection URL.

        Converts standard PostgreSQL URLs to async-compatible URLs using the asyncpg driver.

        Args:
            v: The pre-existing value of ASYNC_DATABASE_URL, if any.
            info: Pydantic Field Validation Info object.

        Returns:
            Any: The compiled asynchronous PostgreSQL connection string.
        """
        if v:
            return v
        
        # Check values in data dict
        values = info.data
        db_url = values.get("DATABASE_URL") or values.get("ADMIN_DB_CONNECTION")
        if not db_url:
            # Check environment variables directly if not loaded yet
            db_url = os.getenv("DATABASE_URL") or os.getenv("ADMIN_DB_CONNECTION")
            
        if not db_url:
            # Fallback to default postgres if nothing is specified
            db_url = "postgresql://postgres:postgres@localhost:5432/erp"
            
        # Convert standard postgresql:// to postgresql+asyncpg:// for SQLAlchemy async
        if db_url.startswith("postgresql://"):
            return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgres://"):
            return db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif not db_url.startswith("postgresql+asyncpg://"):
            # If it's already got another driver or is sqlite, etc.
            return db_url
            
        return db_url

settings = Settings()
# Initialize the computed fields
if not settings.ASYNC_DATABASE_URL:
    db_url = settings.DATABASE_URL or settings.ADMIN_DB_CONNECTION or "postgresql://postgres:postgres@localhost:5432/erp"
    if db_url.startswith("postgresql://"):
        settings.ASYNC_DATABASE_URL = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        settings.ASYNC_DATABASE_URL = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    else:
        settings.ASYNC_DATABASE_URL = db_url
