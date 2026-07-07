from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import String, Numeric, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    manager_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"), nullable=True)

    employees: Mapped[List["Employee"]] = relationship(
        "Employee", 
        back_populates="department",
        foreign_keys="[Employee.department_id]"
    )

class Employee(Base, TimestampMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    job_title: Mapped[str] = mapped_column(String(100), nullable=False)
    salary: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # active, terminated, on_leave

    department: Mapped[Optional["Department"]] = relationship(
        "Department",
        back_populates="employees",
        foreign_keys=[department_id]
    )
    
    attendance: Mapped[List["AttendanceLog"]] = relationship(back_populates="employee", cascade="all, delete-orphan")
    leave_requests: Mapped[List["LeaveRequest"]] = relationship(
        "LeaveRequest",
        back_populates="employee",
        foreign_keys="[LeaveRequest.employee_id]",
        cascade="all, delete-orphan"
    )
    paychecks: Mapped[List["Paycheck"]] = relationship(back_populates="employee", cascade="all, delete-orphan")
    onboarding_tasks: Mapped[List["OnboardingChecklist"]] = relationship(back_populates="employee", cascade="all, delete-orphan")

class AttendanceLog(Base, TimestampMixin):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    clock_in: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    clock_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_hours: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="attendance")

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
    approver: Mapped[Optional["Employee"]] = relationship("Employee", foreign_keys=[approved_by_id])

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
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # draft, paid

    employee: Mapped["Employee"] = relationship(back_populates="paychecks")

class JobPosting(Base, TimestampMixin):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # draft, open, closed

    applications: Mapped[List["Application"]] = relationship(back_populates="job_posting", cascade="all, delete-orphan")

class Candidate(Base, TimestampMixin):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resume_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    applications: Mapped[List["Application"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")

class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_posting_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    application_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="applied", nullable=False)  # applied, screening, interview, offered, hired, rejected

    job_posting: Mapped["JobPosting"] = relationship(back_populates="applications")
    candidate: Mapped["Candidate"] = relationship(back_populates="applications")

class OnboardingChecklist(Base, TimestampMixin):
    __tablename__ = "onboarding_checklists"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="onboarding_tasks")
