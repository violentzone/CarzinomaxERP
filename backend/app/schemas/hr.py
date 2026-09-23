from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
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




