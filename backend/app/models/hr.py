from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Numeric, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4

from app.models.base import Base
from app.models.base import TimestampMixin

class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    manager_id: Mapped[Optional[int]] = mapped_column(Numeric, nullable=True)


class AttendanceLog(Base, TimestampMixin):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # References the users table; kept the employee_id name for API/schema stability.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    clock_in: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    clock_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_hours: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)


class LeaveRequest(Base, TimestampMixin):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    leave_type: Mapped[str] = mapped_column(String(50), nullable=False)  # sick, annual, unpaid, parental
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, approved, rejected
    approved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)


class Paycheck(Base, TimestampMixin):
    """
    Paycheck setup for employees
    """
    __tablename__ = "paychecks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    base_salary: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    allowances: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    deductions: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    net_pay: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)


class Payroll(Base, TimestampMixin):
    """
    The table records each time paid to employees
    """
    __tablename__ = "payrolls"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    base_salary: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    allowances: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    deductions: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    pay_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
