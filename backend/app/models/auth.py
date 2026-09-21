import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    FINANCE = "finance"
    SCM = "scm"
    HR = "hr"
    DEVELOPER = "developer"
    EMPLOYEE = "employee"

class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.EMPLOYEE.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    has_finance_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_scm_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_hr_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_dev_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Access tokens issued before this instant are rejected. Set by logout; NULL = nothing revoked.
    tokens_valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
