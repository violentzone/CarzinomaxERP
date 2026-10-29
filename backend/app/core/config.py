import os
from typing import Any, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Carzinomax Dev"
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

    # GitHub stars/downloads sync (app/core/github.py, scheduler job "github_sync")
    GITHUB_TOKEN: str = ""                 # optional PAT; required for private repos, lifts the limit to 5000 req/h
    GITHUB_SYNC_CRON: str = "0 */6 * * *"  # crontab; APScheduler counts day-of-week from Monday = 0

    # Finance expense status refresh (scheduler job "expense_status")
    EXPENSE_STATUS_CRON: str = "5 0 * * *"  # crontab; daily shortly after midnight so an unpaid bill turns overdue the day after its due date
    
    # Async database URL computed automatically
    ASYNC_DATABASE_URL: str = ""
    LLM_TYPE: str = "remote"
    LLM_API_BASE: str = ""
    LLM_MODEL: str = ""
    LLM_API_KEY: str = ""

    # Outgoing mail (app/core/scheduler.py send_email): SMTP with a Google App Password
    # Required, sourced from .env, no defaults so nothing provider-specific is hard-coded here
    SMTP_HOSTNAME: str                        # e.g. smtp.gmail.com
    SMTP_PORT: int                            # 587 = STARTTLS, 465 = implicit SSL
    SMTP_PASSWORD: str                        # the 16-char Google App Password
    MAIL_FROM: str                            # mailbox login and the From address

    # Project summary mail schedule (the `summary_mail` job is planned, not registered yet)
    # TIME and FREQ are required from .env; WEEKDAY is required only when FREQ=week, MONTHDAY only when FREQ=month
    # Hour is server local time, the job fires at minute 0
    SUMMARY_SEND_TIME: int                    # 0-23
    SUMMARY_SEND_FREQ: str                    # day | week | month
    SUMMARY_SEND_WEEKDAY: int | None = None   # 0-6, Monday = 0 (APScheduler convention)
    SUMMARY_SEND_MONTHDAY: int | None = None  # 1-31; 29-31 skip shorter months

    # Chat attachments (app/core/uploads.py, POST /chatbot/upload): stored on disk under <UPLOAD_DIR>/<user_id>/, no table, kept forever
    UPLOAD_DIR: str = "uploads"               # relative to backend/ unless absolute
    UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024  # per file on the wire, before images are downscaled

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

    @field_validator("SUMMARY_SEND_WEEKDAY", "SUMMARY_SEND_MONTHDAY", mode="before")
    @classmethod
    def blank_summary_day_is_none(cls, v: Any) -> Any:
        """A blank .env line (`SUMMARY_SEND_WEEKDAY=`) arrives as '' and must mean 'not set', not an int parse error."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("SUMMARY_SEND_TIME")
    @classmethod
    def check_summary_send_time(cls, v: int) -> int:
        if not 0 <= v <= 23:
            raise ValueError(f"SUMMARY_SEND_TIME must be an hour between 0 and 23, got {v}")
        return v

    @field_validator("SUMMARY_SEND_FREQ", mode="before")
    @classmethod
    def check_summary_send_freq(cls, v: Any) -> str:
        v = str(v).strip().lower()
        if v not in ("day", "week", "month"):
            raise ValueError(f"SUMMARY_SEND_FREQ must be one of day, week or month, got '{v}'")
        return v

    @field_validator("SUMMARY_SEND_WEEKDAY")
    @classmethod
    def check_summary_send_weekday(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not 0 <= v <= 6:
            raise ValueError(f"SUMMARY_SEND_WEEKDAY must be between 0 (Monday) and 6 (Sunday), got {v}")
        return v

    @field_validator("SUMMARY_SEND_MONTHDAY")
    @classmethod
    def check_summary_send_monthday(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not 1 <= v <= 31:
            raise ValueError(f"SUMMARY_SEND_MONTHDAY must be between 1 and 31, got {v}")
        return v

    @model_validator(mode="after")
    def check_summary_schedule(self) -> "Settings":
        """The day field that SUMMARY_SEND_FREQ needs must be present."""
        if self.SUMMARY_SEND_FREQ == "week" and self.SUMMARY_SEND_WEEKDAY is None:
            raise ValueError("SUMMARY_SEND_WEEKDAY is required when SUMMARY_SEND_FREQ=week")
        if self.SUMMARY_SEND_FREQ == "month" and self.SUMMARY_SEND_MONTHDAY is None:
            raise ValueError("SUMMARY_SEND_MONTHDAY is required when SUMMARY_SEND_FREQ=month")
        return self

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
