from datetime import date, datetime, timezone
from typing import Annotated, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from decimal import Decimal

from app.api.deps import get_db, RoleChecker
from app.models.hr import (
    Department, Employee, AttendanceLog, LeaveRequest, Paycheck,
    JobPosting, Candidate, Application, OnboardingChecklist
)
from app.schemas.hr import (
    DepartmentCreate, DepartmentResponse,
    EmployeeCreate, EmployeeResponse,
    AttendanceLogCreate, AttendanceLogResponse,
    LeaveRequestCreate, LeaveRequestResponse,
    PaycheckCreate, PaycheckResponse,
    JobPostingCreate, JobPostingResponse,
    CandidateCreate, CandidateResponse,
    ApplicationCreate, ApplicationResponse,
    OnboardingChecklistCreate, OnboardingChecklistResponse
)

router = APIRouter(dependencies=[Depends(RoleChecker(["hr", "admin"]))])

# --- Departments ---
@router.post("/departments", response_model=DepartmentResponse)
async def create_department(
    db: Annotated[AsyncSession, Depends(get_db)],
    dept_in: DepartmentCreate
) -> Any:
    """Create a new company department.

    Args:
        db: The database session dependency.
        dept_in: The department creation payload.

    Returns:
        Any: The created Department database instance.

    Raises:
        HTTPException: If a department with the same code already exists.
    """
    result = await db.execute(select(Department).filter(Department.code == dept_in.code))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department code already exists."
        )
    db_dept = Department(**dept_in.model_dump())
    db.add(db_dept)
    await db.commit()
    await db.refresh(db_dept)
    return db_dept

@router.get("/departments", response_model=List[DepartmentResponse])
async def list_departments(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """List all departments in the organization.

    Args:
        db: The database session dependency.

    Returns:
        Any: A list of Department database instances.
    """
    result = await db.execute(select(Department))
    return result.scalars().all()

# --- Employees ---
@router.post("/employees", response_model=EmployeeResponse)
async def create_employee(
    db: Annotated[AsyncSession, Depends(get_db)],
    emp_in: EmployeeCreate
) -> Any:
    """Register/hire a new employee.

    Args:
        db: The database session dependency.
        emp_in: The employee creation details.

    Returns:
        Any: The created Employee database instance.

    Raises:
        HTTPException: If the email already exists or the specified department is not found.
    """
    result = await db.execute(select(Employee).filter(Employee.email == emp_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee email already exists."
        )
    
    if emp_in.department_id:
        dept_res = await db.execute(select(Department).filter(Department.id == emp_in.department_id))
        if not dept_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found."
            )
            
    db_emp = Employee(**emp_in.model_dump())
    db.add(db_emp)
    await db.commit()
    await db.refresh(db_emp)
    return db_emp

@router.get("/employees", response_model=List[EmployeeResponse])
async def list_employees(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100
) -> Any:
    """List all employees in the organization.

    Args:
        db: The database session dependency.
        skip: The number of records to skip (for pagination).
        limit: The maximum number of records to return.

    Returns:
        Any: A list of Employee database instances.
    """
    result = await db.execute(select(Employee).offset(skip).limit(limit))
    return result.scalars().all()

# --- Time & Attendance ---
@router.post("/attendance/clock-in", response_model=AttendanceLogResponse)
async def clock_in(
    employee_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Record a clock-in event for an employee.

    Args:
        employee_id: The ID of the employee clocking in.
        db: The database session dependency.

    Returns:
        Any: The created AttendanceLog database instance.

    Raises:
        HTTPException: If the employee doesn't exist, or is already clocked in without a clock-out.
    """
    # Check employee
    emp_res = await db.execute(select(Employee).filter(Employee.id == employee_id))
    if not emp_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    today = date.today()
    # Check if already clocked in today
    att_res = await db.execute(
        select(AttendanceLog)
        .filter(AttendanceLog.employee_id == employee_id, AttendanceLog.date == today)
    )
    existing = att_res.scalars().all()
    for log in existing:
        if log.clock_out is None:
            raise HTTPException(status_code=400, detail="Employee is already clocked in and hasn't clocked out yet.")
            
    db_log = AttendanceLog(
        employee_id=employee_id,
        date=today,
        clock_in=datetime.now(timezone.utc)
    )
    db.add(db_log)
    await db.commit()
    await db.refresh(db_log)
    return db_log

@router.post("/attendance/clock-out", response_model=AttendanceLogResponse)
async def clock_out(
    employee_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Record a clock-out event for an employee and calculate hours worked.

    Args:
        employee_id: The ID of the employee clocking out.
        db: The database session dependency.

    Returns:
        Any: The updated AttendanceLog database instance.

    Raises:
        HTTPException: If no active clock-in event is found for today.
    """
    today = date.today()
    # Find active clock in
    att_res = await db.execute(
        select(AttendanceLog)
        .filter(
            AttendanceLog.employee_id == employee_id,
            AttendanceLog.date == today,
            AttendanceLog.clock_out == None
        )
    )
    log = att_res.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=400, detail="Active clock-in not found for today.")
        
    now = datetime.now(timezone.utc)
    log.clock_out = now
    
    # Calculate duration in decimal hours
    duration = now - log.clock_in
    hours = Decimal(str(duration.total_seconds() / 3600.0))
    log.total_hours = float(round(hours, 2))
    
    await db.commit()
    await db.refresh(log)
    return log

# --- Leave Requests ---
@router.post("/leaves", response_model=LeaveRequestResponse)
async def create_leave_request(
    db: Annotated[AsyncSession, Depends(get_db)],
    leave_in: LeaveRequestCreate
) -> Any:
    """Submit a new employee leave request.

    Args:
        db: The database session dependency.
        leave_in: The leave request details.

    Returns:
        Any: The created LeaveRequest database instance.
    """
    db_leave = LeaveRequest(**leave_in.model_dump())
    db.add(db_leave)
    await db.commit()
    await db.refresh(db_leave)
    return db_leave

# --- Paychecks ---
@router.post("/paychecks", response_model=PaycheckResponse)
async def create_paycheck(
    db: Annotated[AsyncSession, Depends(get_db)],
    paycheck_in: PaycheckCreate
) -> Any:
    """Generate and record a paycheck for an employee.

    Calculates net pay as (base salary + allowances - deductions).

    Args:
        db: The database session dependency.
        paycheck_in: The paycheck details.

    Returns:
        Any: The created Paycheck database instance.
    """
    base = Decimal(str(paycheck_in.base_salary))
    allowances = Decimal(str(paycheck_in.allowances))
    deductions = Decimal(str(paycheck_in.deductions))
    net = base + allowances - deductions
    
    db_pay = Paycheck(
        employee_id=paycheck_in.employee_id,
        pay_period_start=paycheck_in.pay_period_start,
        pay_period_end=paycheck_in.pay_period_end,
        base_salary=paycheck_in.base_salary,
        allowances=paycheck_in.allowances,
        deductions=paycheck_in.deductions,
        net_pay=float(net),
        payment_date=paycheck_in.payment_date,
        status=paycheck_in.status,
    )
    db.add(db_pay)
    await db.commit()
    await db.refresh(db_pay)
    return db_pay
