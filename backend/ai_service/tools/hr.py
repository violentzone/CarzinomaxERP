""" Function tools for HR module"""
from typing import Literal
from datetime import datetime
from app.core.database import SessionLocal
from app.core.log_module import user_log, system_log
from sqlalchemy import select

from app.models import Employee, AttendanceLog
from uuid import uuid4

async def operate_employee(operate_caller: int, operation: Literal['create', 'update', 'delete'], name: str, salary: float, department_id: int=None, email: str|None=None, job_title: str|None=None,
                     ) -> bool:
    """
    Tool for LLM to operate on Employee table in database
    Args:
        operate_caller (int): System user who call this tool
        operation (str): CRUD operation in string format
        name (str): Employee name
        salary (float): Employee salary
        department_id (int)(optional): Department id of employee, required if create employee or update to different department
        email (str): Employee email
        job_title (str): Employee job title


    Returns:
        True if successful, False otherwise
    """
    _user_log = user_log(operate_caller)
    _user_log.info(f'Call `operate_employee`: {operation}')
    try:
        if operation == 'create':
            _id = uuid4()
            hire_date = datetime.now().date()
            employee = Employee(name=name, salary=salary, department_id=department_id, id=_id, email=email,
                                hire_date=hire_date, job_title=job_title, status='active')
            async with SessionLocal() as session:
                session.add(employee)
                await session.commit()
            _user_log.info(f'User {name} created')

        elif operation == 'update':
            # Get user with name
            async with SessionLocal() as session:
                stmt = select(Employee).where(Employee.name == name)
                result = await session.execute(stmt)
                user = result.scalar_one()
                _user_log.info(f'Updating {name}...')
                
                # Dynamically set fields that are not None
                update_data = {
                    "salary": salary,
                    "department_id": department_id,
                    "email": email,
                    "job_title": job_title,
                }
                for field, value in update_data.items():
                    if value is not None:
                        setattr(user, field, value)
                        
                await session.commit()
                _user_log.info(f'User {name} updated')

        elif operation == 'delete':
            # Get user with name and delete
            async with SessionLocal() as session:
                stmt = select(Employee).where(Employee.name == name)
                result = await session.execute(stmt)
                user = result.scalar_one()
                await session.delete(user)
                await session.commit()
            _user_log.info(f'User {name} deleted')
        else:
            raise AssertionError(f'Operation {operation} not supported')
        return True

    except Exception as err:
        _user_log.error('Unexpect error:\n' + str(err))
        return False

async def clock_in_or_out(operate_caller: int, employee_name: str, operation: Literal['clock-in', 'clock-out'], time: datetime) -> bool:
    """
    Clock in or clock out for an employee
    Args:
        operate_caller (int): System user who call this tool
        employee_name (str): Employee name:
        operation (str):  Clock-in or Clock-out in string
        time (datetime): Datetime of operation

    Returns:
         True if successful, False otherwise
    """
    _user_log = user_log(operate_caller)
    _user_log.info(f'Call `clock_in_or_out` for {employee_name}: {operation}')
    try:
        async with SessionLocal() as session:
            # 1. Fetch employee
            stmt = select(Employee).where(Employee.name == employee_name)
            res = await session.execute(stmt)
            employee = res.scalar_one_or_none()
            if not employee:
                _user_log.error(f"Employee not found: {employee_name}")
                return False

            input_date = time.date()

            if operation == 'clock-in':
                # 2. Check if already clocked in on input date without clocking out
                att_res = await session.execute(
                    select(AttendanceLog)
                    .filter(AttendanceLog.employee_id == employee.id, AttendanceLog.date == input_date)
                )
                existing = att_res.scalars().all()
                for log in existing:
                    if log.clock_out is None:
                        _user_log.error(f"Employee {employee_name} is already clocked in and hasn't clocked out yet.")
                        return False

                # 3. Create clock-in log
                db_log = AttendanceLog(
                    employee_id=employee.id,
                    date=input_date,
                    clock_in=time
                )
                session.add(db_log)
                await session.commit()
                _user_log.info(f"Employee {employee_name} clocked in successfully at {time}")

            elif operation == 'clock-out':
                # 2. Find active clock-in for input date
                att_res = await session.execute(
                    select(AttendanceLog)
                    .filter(
                        AttendanceLog.employee_id == employee.id,
                        AttendanceLog.date == input_date,
                        AttendanceLog.clock_out == None
                    )
                )
                log = att_res.scalar_one_or_none()
                if not log:
                    _user_log.error(f"Active clock-in not found on date {input_date} for employee {employee_name}")
                    return False

                # Ensure timezone alignment to avoid subtraction TypeError
                if log.clock_in.tzinfo is not None and time.tzinfo is None:
                    time = time.replace(tzinfo=log.clock_in.tzinfo)
                elif log.clock_in.tzinfo is None and time.tzinfo is not None:
                    time = time.replace(tzinfo=None)

                # 3. Update clock-out and calculate hours
                log.clock_out = time
                duration = time - log.clock_in
                hours = duration.total_seconds() / 3600.0
                log.total_hours = float(round(hours, 2))

                await session.commit()
                _user_log.info(f"Employee {employee_name} clocked out successfully at {time}, total hours: {log.total_hours}")

            else:
                raise AssertionError(f'Operation {operation} not supported')

        return True
    except Exception as err:
        _user_log.error('Unexpected error in clock_in_or_out:\n' + str(err))
        return False
