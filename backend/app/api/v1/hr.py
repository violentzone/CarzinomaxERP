from datetime import date, datetime, timezone
from typing import Annotated, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import update
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
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    AttendanceLogCreate, AttendanceLogUpdate, AttendanceLogResponse,
    LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestResponse,
    PaycheckCreate, PaycheckUpdate, PaycheckResponse,
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

@router.put("/departments/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    dept_in: DepartmentUpdate
) -> Any:
    """Update a department. Only the provided fields are changed.

    Args:
        department_id: The ID of the department to update.
        db: The database session dependency.
        dept_in: The fields to update.

    Returns:
        Any: The updated Department database instance.

    Raises:
        HTTPException: If the department is not found, or the new code is taken.
    """
    result = await db.execute(select(Department).filter(Department.id == department_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")

    data = dept_in.model_dump(exclude_unset=True)

    if "code" in data and data["code"] != dept.code:
        dup_res = await db.execute(select(Department).filter(Department.code == data["code"]))
        if dup_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department code already exists."
            )

    for key, value in data.items():
        setattr(dept, key, value)
    await db.commit()
    await db.refresh(dept)
    return dept

@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a department. Employees in the department are unassigned.

    Args:
        department_id: The ID of the department to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the department is not found, or job postings still reference it.
    """
    result = await db.execute(
        select(Department)
        .options(selectinload(Department.employees))
        .filter(Department.id == department_id)
    )
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")

    posting_res = await db.execute(
        select(JobPosting.id).filter(JobPosting.department_id == department_id).limit(1)
    )
    if posting_res.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department has job postings and cannot be deleted."
        )

    await db.delete(dept)
    await db.commit()

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

@router.put("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    emp_in: EmployeeUpdate
) -> Any:
    """Update an employee. Only the provided fields are changed.

    Args:
        employee_id: The ID of the employee to update.
        db: The database session dependency.
        emp_in: The fields to update.

    Returns:
        Any: The updated Employee database instance.

    Raises:
        HTTPException: If the employee is not found, the new email is taken,
            or the new department doesn't exist.
    """
    result = await db.execute(select(Employee).filter(Employee.id == employee_id))
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")

    data = emp_in.model_dump(exclude_unset=True)

    if "email" in data and data["email"] != emp.email:
        dup_res = await db.execute(select(Employee).filter(Employee.email == data["email"]))
        if dup_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee email already exists."
            )

    if data.get("department_id"):
        dept_res = await db.execute(select(Department).filter(Department.id == data["department_id"]))
        if not dept_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found."
            )

    for key, value in data.items():
        setattr(emp, key, value)
    await db.commit()
    await db.refresh(emp)
    return emp

@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete an employee along with their attendance, leave and payroll records.

    Departments managed by the employee and leave requests they approved are
    unlinked rather than deleted.

    Args:
        employee_id: The ID of the employee to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the employee is not found.
    """
    result = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.attendance),
            selectinload(Employee.leave_requests),
            selectinload(Employee.paychecks),
            selectinload(Employee.onboarding_tasks),
        )
        .filter(Employee.id == employee_id)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")

    await db.execute(
        update(Department).where(Department.manager_id == employee_id).values(manager_id=None)
    )
    await db.execute(
        update(LeaveRequest).where(LeaveRequest.approved_by_id == employee_id).values(approved_by_id=None)
    )

    await db.delete(emp)
    await db.commit()

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

@router.put("/attendance/{log_id}", response_model=AttendanceLogResponse)
async def update_attendance_log(
    log_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    log_in: AttendanceLogUpdate
) -> Any:
    """Correct an attendance log's clock-in/out times. Total hours and the
    log date are recalculated from the new times.

    Args:
        log_id: The ID of the attendance log to update.
        db: The database session dependency.
        log_in: The corrected clock-in and/or clock-out times.

    Returns:
        Any: The updated AttendanceLog database instance.

    Raises:
        HTTPException: If the log is not found, or clock-out precedes clock-in.
    """
    result = await db.execute(select(AttendanceLog).filter(AttendanceLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance log not found.")

    data = log_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(log, key, value)

    if log.clock_in and log.clock_out:
        clock_in = log.clock_in if log.clock_in.tzinfo else log.clock_in.replace(tzinfo=timezone.utc)
        clock_out = log.clock_out if log.clock_out.tzinfo else log.clock_out.replace(tzinfo=timezone.utc)
        if clock_out < clock_in:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Clock-out cannot be before clock-in."
            )
        duration = clock_out - clock_in
        log.total_hours = float(round(Decimal(str(duration.total_seconds() / 3600.0)), 2))
    else:
        log.total_hours = None

    if log.clock_in:
        log.date = log.clock_in.date()

    await db.commit()
    await db.refresh(log)
    return log

@router.delete("/attendance/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attendance_log(
    log_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete an attendance log.

    Args:
        log_id: The ID of the attendance log to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the log is not found.
    """
    result = await db.execute(select(AttendanceLog).filter(AttendanceLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance log not found.")

    await db.delete(log)
    await db.commit()

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

@router.put("/leaves/{leave_id}", response_model=LeaveRequestResponse)
async def update_leave_request(
    leave_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    leave_in: LeaveRequestUpdate
) -> Any:
    """Update a leave request. Only the provided fields are changed.

    Args:
        leave_id: The ID of the leave request to update.
        db: The database session dependency.
        leave_in: The fields to update.

    Returns:
        Any: The updated LeaveRequest database instance.

    Raises:
        HTTPException: If the leave request or a new employee is not found.
    """
    result = await db.execute(select(LeaveRequest).filter(LeaveRequest.id == leave_id))
    leave = result.scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found.")

    data = leave_in.model_dump(exclude_unset=True)

    if data.get("employee_id"):
        emp_res = await db.execute(select(Employee).filter(Employee.id == data["employee_id"]))
        if not emp_res.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")

    for key, value in data.items():
        setattr(leave, key, value)
    await db.commit()
    await db.refresh(leave)
    return leave

@router.delete("/leaves/{leave_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_leave_request(
    leave_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a leave request.

    Args:
        leave_id: The ID of the leave request to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the leave request is not found.
    """
    result = await db.execute(select(LeaveRequest).filter(LeaveRequest.id == leave_id))
    leave = result.scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found.")

    await db.delete(leave)
    await db.commit()

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

@router.put("/paychecks/{paycheck_id}", response_model=PaycheckResponse)
async def update_paycheck(
    paycheck_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    paycheck_in: PaycheckUpdate
) -> Any:
    """Update a paycheck. Net pay is recalculated from the resulting amounts.

    Args:
        paycheck_id: The ID of the paycheck to update.
        db: The database session dependency.
        paycheck_in: The fields to update.

    Returns:
        Any: The updated Paycheck database instance.

    Raises:
        HTTPException: If the paycheck is not found.
    """
    result = await db.execute(select(Paycheck).filter(Paycheck.id == paycheck_id))
    paycheck = result.scalar_one_or_none()
    if not paycheck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paycheck not found.")

    data = paycheck_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(paycheck, key, value)

    net = (
        Decimal(str(paycheck.base_salary))
        + Decimal(str(paycheck.allowances))
        - Decimal(str(paycheck.deductions))
    )
    paycheck.net_pay = float(net)

    await db.commit()
    await db.refresh(paycheck)
    return paycheck

@router.delete("/paychecks/{paycheck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paycheck(
    paycheck_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> None:
    """Delete a paycheck record.

    Args:
        paycheck_id: The ID of the paycheck to delete.
        db: The database session dependency.

    Raises:
        HTTPException: If the paycheck is not found.
    """
    result = await db.execute(select(Paycheck).filter(Paycheck.id == paycheck_id))
    paycheck = result.scalar_one_or_none()
    if not paycheck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paycheck not found.")

    await db.delete(paycheck)
    await db.commit()
