from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from decimal import Decimal

# Department
class DepartmentBase(BaseModel):
    code: str
    name: str
    manager_id: Optional[int] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    manager_id: Optional[int] = None

class DepartmentResponse(DepartmentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Employee
class EmployeeBase(BaseModel):
    user_id: Optional[int] = None
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    hire_date: date
    department_id: Optional[int] = None
    job_title: str
    salary: Decimal = Field(default=Decimal("0.0"))
    status: str = "active"

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    user_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    hire_date: Optional[date] = None
    department_id: Optional[int] = None
    job_title: Optional[str] = None
    salary: Optional[Decimal] = None
    status: Optional[str] = None

class EmployeeResponse(EmployeeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Attendance Log
class AttendanceLogBase(BaseModel):
    employee_id: int
    date: date
    clock_in: datetime
    clock_out: Optional[datetime] = None

class AttendanceLogCreate(AttendanceLogBase):
    pass

class AttendanceLogUpdate(BaseModel):
    clock_in: Optional[datetime] = None
    clock_out: Optional[datetime] = None

class AttendanceLogResponse(AttendanceLogBase):
    id: int
    total_hours: Optional[Decimal] = None
    model_config = ConfigDict(from_attributes=True)

# Leave Request
class LeaveRequestBase(BaseModel):
    employee_id: int
    leave_type: str
    start_date: date
    end_date: date
    reason: Optional[str] = None
    status: str = "pending"
    approved_by_id: Optional[int] = None

class LeaveRequestCreate(LeaveRequestBase):
    pass

class LeaveRequestUpdate(BaseModel):
    employee_id: Optional[int] = None
    leave_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    approved_by_id: Optional[int] = None

class LeaveRequestResponse(LeaveRequestBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Paycheck
class PaycheckBase(BaseModel):
    employee_id: int
    pay_period_start: date
    pay_period_end: date
    base_salary: Decimal
    allowances: Decimal = Field(default=Decimal("0.0"))
    deductions: Decimal = Field(default=Decimal("0.0"))
    payment_date: Optional[date] = None
    status: str = "draft"

class PaycheckCreate(PaycheckBase):
    pass

class PaycheckUpdate(BaseModel):
    employee_id: Optional[int] = None
    pay_period_start: Optional[date] = None
    pay_period_end: Optional[date] = None
    base_salary: Optional[Decimal] = None
    allowances: Optional[Decimal] = None
    deductions: Optional[Decimal] = None
    payment_date: Optional[date] = None
    status: Optional[str] = None

class PaycheckResponse(PaycheckBase):
    id: int
    net_pay: Decimal
    model_config = ConfigDict(from_attributes=True)

# Job Posting
class JobPostingBase(BaseModel):
    title: str
    department_id: int
    description: str
    status: str = "draft"

class JobPostingCreate(JobPostingBase):
    pass

class JobPostingResponse(JobPostingBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Candidate
class CandidateBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    resume_url: Optional[str] = None

class CandidateCreate(CandidateBase):
    pass

class CandidateResponse(CandidateBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Application
class ApplicationBase(BaseModel):
    job_posting_id: int
    candidate_id: int
    application_date: date
    status: str = "applied"

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationResponse(ApplicationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Onboarding Checklist
class OnboardingChecklistBase(BaseModel):
    employee_id: int
    task_name: str
    is_completed: bool = False
    completed_at: Optional[datetime] = None

class OnboardingChecklistCreate(OnboardingChecklistBase):
    pass

class OnboardingChecklistResponse(OnboardingChecklistBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
