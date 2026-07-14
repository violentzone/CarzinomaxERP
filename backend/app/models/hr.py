from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import String, Numeric, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    manager_id: Mapped[Optional[int]] = mapped_column(Numeric, nullable=True)

    employees: Mapped[List["Employee"]] = relationship("Employee", back_populates="department")

class Employee(Base, TimestampMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    job_title: Mapped[str] = mapped_column(String(100), nullable=True)
    salary: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # active, terminated, on_leave

    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="employees")
    attendance: Mapped[List["AttendanceLog"]] = relationship("AttendanceLog", back_populates="employee", cascade="all, delete-orphan")
    leave_requests: Mapped[List["LeaveRequest"]] = relationship("LeaveRequest", foreign_keys="[LeaveRequest.employee_id]", back_populates="employee", cascade="all, delete-orphan")
    approved_leaves: Mapped[List["LeaveRequest"]] = relationship("LeaveRequest", foreign_keys="[LeaveRequest.approved_by_id]", back_populates="approver")
    paychecks: Mapped[List["Paycheck"]] = relationship("Paycheck", back_populates="employee", cascade="all, delete-orphan")


class AttendanceLog(Base, TimestampMixin):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    clock_in: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    clock_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_hours: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="attendance")


class LeaveRequest(Base, TimestampMixin):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    leave_type: Mapped[str] = mapped_column(String(50), nullable=False)  # sick, annual, unpaid, parental
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, approved, rejected
    approved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"), nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", foreign_keys=[employee_id], back_populates="leave_requests")
    approver: Mapped[Optional["Employee"]] = relationship("Employee", foreign_keys=[approved_by_id], back_populates="approved_leaves")

class Paycheck(Base, TimestampMixin):
    __tablename__ = "paychecks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    pay_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    pay_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    base_salary: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    allowances: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    deductions: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    net_pay: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    payment_date: Mapped[int] = mapped_column(Numeric, nullable=False, doc='Pay day in a month')
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # draft, paid

    employee: Mapped["Employee"] = relationship("Employee", back_populates="paychecks")
