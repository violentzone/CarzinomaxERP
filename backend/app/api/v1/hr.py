"""
HR module, Query, add, remove and update User, Department, AttendanceLog, LeaveRequest and Paycheck
"""
from datetime import date as date_type, datetime
from traceback import format_exc

from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse as Response
from pydantic import BaseModel
from sqlalchemy import select
from starlette import status

from app.api.common import get_current_user, permission_check
from app.core.database import get_db
from app.core.log_module import user_log
from app.core.security import get_password_hash
from app.models import AttendanceLog, Department, LeaveRequest, Paycheck, User

hr_router = APIRouter(prefix="/hr", tags=["HR"])


@hr_router.get("/employee_list")
@hr_router.get("/user_list")
async def get_user_list(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get all users in the database.
    Args:
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified list of User objects
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info('Query all users')
    users = (await db.scalars(select(User))).all()
    data = []
    for u in users:
        data.append(u.to_dict())
    log.info(f"{str(len(data))} users found")

    return Response({
        "status": "success",
        "data": data,
    }, status_code=status.HTTP_200_OK, media_type='application/json')


@hr_router.get("/employee/{user_id}")
@hr_router.get("/user/{user_id}")
async def get_user(user_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get user by id
    Args:
        user_id: The user to query
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified user object
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Query user ID: {user_id}')

    user = await db.get(User, user_id)
    if not user:
        log.warning(f'User ID: {user_id} not found')
        return Response({"status": "fail", "error": f"User with id {user_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    user_data = user.to_dict()
    log.info(f'Query user: {user_data}')

    return Response({"status": "success", "data": user_data}, status_code=status.HTTP_200_OK, media_type='application/json')


class CreateUser(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    is_active: bool | None = True
    has_finance_access: bool | None = False
    has_scm_access: bool | None = False
    has_hr_access: bool | None = False
    has_dev_access: bool | None = False
    tokens_valid_from: datetime | None = None


class UpdateUser(BaseModel):
    email: str | None = None
    password: str | None = None
    full_name: str | None = None
    is_active: bool | None = None
    has_finance_access: bool | None = None
    has_scm_access: bool | None = None
    has_hr_access: bool | None = None
    has_dev_access: bool | None = None
    tokens_valid_from: datetime | None = None


@hr_router.post("/user")
async def create_user(new_user: CreateUser, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Create a new user
    Args:
        new_user: New user information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success', 'data': user}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Create user with email: {new_user.email}')

    try:
        existing_user = await db.scalar(select(User).where(User.email == new_user.email))
        if existing_user:
            log.warning(f'User with email {new_user.email} already exists')
            return Response({"status": "fail", "error": f"User with email '{new_user.email}' already exists"}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')

        user = User(
            email=new_user.email,
            hashed_password=get_password_hash(new_user.password),
            full_name=new_user.full_name,
            is_active=new_user.is_active if new_user.is_active is not None else True,
            has_finance_access=bool(new_user.has_finance_access),
            has_scm_access=bool(new_user.has_scm_access),
            has_hr_access=bool(new_user.has_hr_access),
            has_dev_access=bool(new_user.has_dev_access),
            tokens_valid_from=new_user.tokens_valid_from,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_data = user.to_dict()
        log.info(f'User created: {user_data}')
        return Response({"status": "success", "data": user_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to create user: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@hr_router.put("/user/{user_id}")
async def update_user(user_id: int, new_user: UpdateUser, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Update user by id
    Args:
        user_id: User ID to update
        new_user: New user information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Update user ID: {user_id}')

    old_user = await db.get(User, user_id)
    if not old_user:
        log.warning(f'User ID: {user_id} not found')
        return Response({"status": "fail", "error": f"User with id {user_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        for field_name, field_value in new_user:
            if field_value is not None:
                if field_name == "password":
                    old_user.hashed_password = get_password_hash(field_value)
                    log.info(f'Password updated and hashed for user ID: {user_id}')
                else:
                    setattr(old_user, field_name, field_value)
        await db.commit()
        await db.refresh(old_user)
        log.info(f'User updated: {old_user.to_dict()}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to update user: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@hr_router.delete("/user/{user_id}")
async def delete_user(user_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Delete user by id
    Args:
        user_id: User ID to delete
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Delete user ID: {user_id}')

    user = await db.get(User, user_id)
    if not user:
        log.warning(f'User ID: {user_id} not found')
        return Response({"status": "fail", "error": f"User with id {user_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(user)
        await db.commit()
        log.info(f'User deleted ID: {user_id}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to delete user: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------

@hr_router.get("/department_list")
async def get_department_list(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get all departments in the database.
    Args:
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified list of Department objects
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info('Query all departments')
    departments = (await db.scalars(select(Department))).all()
    data = []
    for d in departments:
        data.append(d.to_dict())
    log.info(f"{str(len(data))} departments found")

    return Response({
        "status": "success",
        "data": data,
    }, status_code=status.HTTP_200_OK, media_type='application/json')


@hr_router.get("/department/{department_id}")
async def get_department(department_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get department by id
    Args:
        department_id: The department to query
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified department object
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Query department ID: {department_id}')

    department = await db.get(Department, department_id)
    if not department:
        log.warning(f'Department ID: {department_id} not found')
        return Response({"status": "fail", "error": f"Department with id {department_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    department_data = department.to_dict()
    log.info(f'Query department: {department_data}')

    return Response({"status": "success", "data": department_data}, status_code=status.HTTP_200_OK, media_type='application/json')


class CreateDepartment(BaseModel):
    code: str
    name: str
    manager_id: int | None = None


class UpdateDepartment(BaseModel):
    code: str | None = None
    name: str | None = None
    manager_id: int | None = None


@hr_router.post("/department")
async def create_department(new_department: CreateDepartment, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Create a new department
    Args:
        new_department: New department information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success', 'data': department}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Create department with code: {new_department.code}')

    try:
        existing_department = await db.scalar(select(Department).where(Department.code == new_department.code))
        if existing_department:
            log.warning(f'Department with code {new_department.code} already exists')
            return Response({"status": "fail", "error": f"Department with code '{new_department.code}' already exists"}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')

        department = Department(
            code=new_department.code,
            name=new_department.name,
            manager_id=new_department.manager_id,
        )
        db.add(department)
        await db.commit()
        await db.refresh(department)
        department_data = department.to_dict()
        log.info(f'Department created: {department_data}')
        return Response({"status": "success", "data": department_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to create department: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@hr_router.put("/department/{department_id}")
async def update_department(department_id: int, new_department: UpdateDepartment, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Update department by id
    Args:
        department_id: Department ID to update
        new_department: New department information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Update department ID: {department_id}')

    old_department = await db.get(Department, department_id)
    if not old_department:
        log.warning(f'Department ID: {department_id} not found')
        return Response({"status": "fail", "error": f"Department with id {department_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        for field_name, field_value in new_department:
            if field_value is not None:
                setattr(old_department, field_name, field_value)
        await db.commit()
        await db.refresh(old_department)
        log.info(f'Department updated: {old_department.to_dict()}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to update department: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@hr_router.delete("/department/{department_id}")
async def delete_department(department_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Delete department by id
    Args:
        department_id: Department ID to delete
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Delete department ID: {department_id}')

    department = await db.get(Department, department_id)
    if not department:
        log.warning(f'Department ID: {department_id} not found')
        return Response({"status": "fail", "error": f"Department with id {department_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(department)
        await db.commit()
        log.info(f'Department deleted ID: {department_id}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to delete department: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


# ---------------------------------------------------------------------------
# AttendanceLog
# ---------------------------------------------------------------------------

@hr_router.get("/attendance_list")
async def get_attendance_list(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get all attendance logs in the database.
    Args:
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified list of AttendanceLog objects
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info('Query all attendance logs')
    attendance_logs = (await db.scalars(select(AttendanceLog))).all()
    data = []
    for a in attendance_logs:
        data.append(a.to_dict())
    log.info(f"{str(len(data))} attendance logs found")

    return Response({
        "status": "success",
        "data": data,
    }, status_code=status.HTTP_200_OK, media_type='application/json')


@hr_router.get("/attendance/{attendance_id}")
async def get_attendance(attendance_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get attendance log by id
    Args:
        attendance_id: The attendance log to query
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified attendance log object
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Query attendance log ID: {attendance_id}')

    attendance = await db.get(AttendanceLog, attendance_id)
    if not attendance:
        log.warning(f'Attendance log ID: {attendance_id} not found')
        return Response({"status": "fail", "error": f"Attendance log with id {attendance_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    attendance_data = attendance.to_dict()
    log.info(f'Query attendance log: {attendance_data}')

    return Response({"status": "success", "data": attendance_data}, status_code=status.HTTP_200_OK, media_type='application/json')


class CreateAttendance(BaseModel):
    user_id: int
    date: date_type
    clock_in: datetime
    clock_out: datetime | None = None
    total_hours: float | None = None


class UpdateAttendance(BaseModel):
    user_id: int | None = None
    date: date_type | None = None
    clock_in: datetime | None = None
    clock_out: datetime | None = None
    total_hours: float | None = None


@hr_router.post("/attendance")
async def create_attendance(new_attendance: CreateAttendance, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Create a new attendance log
    Args:
        new_attendance: New attendance log information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success', 'data': attendance}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Create attendance log for user ID: {new_attendance.user_id} on {new_attendance.date}')

    try:
        user = await db.get(User, new_attendance.user_id)
        if not user:
            log.warning(f'User ID: {new_attendance.user_id} not found')
            return Response({"status": "fail", "error": f"User with id {new_attendance.user_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

        attendance = AttendanceLog(
            user_id=new_attendance.user_id,
            date=new_attendance.date,
            clock_in=new_attendance.clock_in,
            clock_out=new_attendance.clock_out,
            total_hours=new_attendance.total_hours,
        )
        db.add(attendance)
        await db.commit()
        await db.refresh(attendance)
        attendance_data = attendance.to_dict()
        log.info(f'Attendance log created: {attendance_data}')
        return Response({"status": "success", "data": attendance_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to create attendance log: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@hr_router.put("/attendance/{attendance_id}")
async def update_attendance(attendance_id: int, new_attendance: UpdateAttendance, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Update attendance log by id
    Args:
        attendance_id: Attendance log ID to update
        new_attendance: New attendance log information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Update attendance log ID: {attendance_id}')

    old_attendance = await db.get(AttendanceLog, attendance_id)
    if not old_attendance:
        log.warning(f'Attendance log ID: {attendance_id} not found')
        return Response({"status": "fail", "error": f"Attendance log with id {attendance_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        for field_name, field_value in new_attendance:
            if field_value is not None:
                setattr(old_attendance, field_name, field_value)
        await db.commit()
        await db.refresh(old_attendance)
        log.info(f'Attendance log updated: {old_attendance.to_dict()}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to update attendance log: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@hr_router.delete("/attendance/{attendance_id}")
async def delete_attendance(attendance_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Delete attendance log by id
    Args:
        attendance_id: Attendance log ID to delete
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Delete attendance log ID: {attendance_id}')

    attendance = await db.get(AttendanceLog, attendance_id)
    if not attendance:
        log.warning(f'Attendance log ID: {attendance_id} not found')
        return Response({"status": "fail", "error": f"Attendance log with id {attendance_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(attendance)
        await db.commit()
        log.info(f'Attendance log deleted ID: {attendance_id}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to delete attendance log: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


# ---------------------------------------------------------------------------
# LeaveRequest
# ---------------------------------------------------------------------------

@hr_router.get("/leave_request_list")
async def get_leave_request_list(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get all leave requests in the database.
    Args:
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified list of LeaveRequest objects
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info('Query all leave requests')
    leave_requests = (await db.scalars(select(LeaveRequest))).all()
    data = []
    for lr in leave_requests:
        data.append(lr.to_dict())
    log.info(f"{str(len(data))} leave requests found")

    return Response({
        "status": "success",
        "data": data,
    }, status_code=status.HTTP_200_OK, media_type='application/json')


@hr_router.get("/leave_request/{leave_request_id}")
async def get_leave_request(leave_request_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get leave request by id
    Args:
        leave_request_id: The leave request to query
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified leave request object
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Query leave request ID: {leave_request_id}')

    leave_request = await db.get(LeaveRequest, leave_request_id)
    if not leave_request:
        log.warning(f'Leave request ID: {leave_request_id} not found')
        return Response({"status": "fail", "error": f"Leave request with id {leave_request_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    leave_request_data = leave_request.to_dict()
    log.info(f'Query leave request: {leave_request_data}')

    return Response({"status": "success", "data": leave_request_data}, status_code=status.HTTP_200_OK, media_type='application/json')


class CreateLeaveRequest(BaseModel):
    user_id: int
    leave_type: str  # sick, annual, unpaid, parental
    start_date: date_type
    end_date: date_type
    reason: str | None = None
    status: str | None = "pending"  # pending, approved, rejected
    approved_by_id: int | None = None


class UpdateLeaveRequest(BaseModel):
    user_id: int | None = None
    leave_type: str | None = None
    start_date: date_type | None = None
    end_date: date_type | None = None
    reason: str | None = None
    status: str | None = None
    approved_by_id: int | None = None


@hr_router.post("/leave_request")
async def create_leave_request(new_leave_request: CreateLeaveRequest, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Create a new leave request
    Args:
        new_leave_request: New leave request information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success', 'data': leave_request}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Create leave request for user ID: {new_leave_request.user_id} ({new_leave_request.leave_type})')

    try:
        user = await db.get(User, new_leave_request.user_id)
        if not user:
            log.warning(f'User ID: {new_leave_request.user_id} not found')
            return Response({"status": "fail", "error": f"User with id {new_leave_request.user_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

        if new_leave_request.end_date < new_leave_request.start_date:
            log.warning(f'Leave request end date {new_leave_request.end_date} is before start date {new_leave_request.start_date}')
            return Response({"status": "fail", "error": "end_date must not be before start_date"}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')

        leave_request = LeaveRequest(
            user_id=new_leave_request.user_id,
            leave_type=new_leave_request.leave_type,
            start_date=new_leave_request.start_date,
            end_date=new_leave_request.end_date,
            reason=new_leave_request.reason,
            status=new_leave_request.status if new_leave_request.status is not None else "pending",
            approved_by_id=new_leave_request.approved_by_id,
        )
        db.add(leave_request)
        await db.commit()
        await db.refresh(leave_request)
        leave_request_data = leave_request.to_dict()
        log.info(f'Leave request created: {leave_request_data}')
        return Response({"status": "success", "data": leave_request_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to create leave request: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@hr_router.put("/leave_request/{leave_request_id}")
async def update_leave_request(leave_request_id: int, new_leave_request: UpdateLeaveRequest, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Update leave request by id
    Args:
        leave_request_id: Leave request ID to update
        new_leave_request: New leave request information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Update leave request ID: {leave_request_id}')

    old_leave_request = await db.get(LeaveRequest, leave_request_id)
    if not old_leave_request:
        log.warning(f'Leave request ID: {leave_request_id} not found')
        return Response({"status": "fail", "error": f"Leave request with id {leave_request_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        for field_name, field_value in new_leave_request:
            if field_value is not None:
                setattr(old_leave_request, field_name, field_value)
        if old_leave_request.end_date < old_leave_request.start_date:
            log.warning(f'Leave request end date {old_leave_request.end_date} is before start date {old_leave_request.start_date}')
            await db.rollback()
            return Response({"status": "fail", "error": "end_date must not be before start_date"}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
        await db.commit()
        await db.refresh(old_leave_request)
        log.info(f'Leave request updated: {old_leave_request.to_dict()}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to update leave request: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@hr_router.delete("/leave_request/{leave_request_id}")
async def delete_leave_request(leave_request_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Delete leave request by id
    Args:
        leave_request_id: Leave request ID to delete
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Delete leave request ID: {leave_request_id}')

    leave_request = await db.get(LeaveRequest, leave_request_id)
    if not leave_request:
        log.warning(f'Leave request ID: {leave_request_id} not found')
        return Response({"status": "fail", "error": f"Leave request with id {leave_request_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(leave_request)
        await db.commit()
        log.info(f'Leave request deleted ID: {leave_request_id}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to delete leave request: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


# ---------------------------------------------------------------------------
# Paycheck
# ---------------------------------------------------------------------------

@hr_router.get("/paycheck_list")
async def get_paycheck_list(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get all paychecks in the database.
    Args:
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified list of Paycheck objects
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info('Query all paychecks')
    paychecks = (await db.scalars(select(Paycheck))).all()
    data = []
    for p in paychecks:
        data.append(p.to_dict())
    log.info(f"{str(len(data))} paychecks found")

    return Response({
        "status": "success",
        "data": data,
    }, status_code=status.HTTP_200_OK, media_type='application/json')


@hr_router.get("/paycheck/{paycheck_id}")
async def get_paycheck(paycheck_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get paycheck by id
    Args:
        paycheck_id: The paycheck to query
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified paycheck object
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Query paycheck ID: {paycheck_id}')

    paycheck = await db.get(Paycheck, paycheck_id)
    if not paycheck:
        log.warning(f'Paycheck ID: {paycheck_id} not found')
        return Response({"status": "fail", "error": f"Paycheck with id {paycheck_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    paycheck_data = paycheck.to_dict()
    log.info(f'Query paycheck: {paycheck_data}')

    return Response({"status": "success", "data": paycheck_data}, status_code=status.HTTP_200_OK, media_type='application/json')


class CreatePaycheck(BaseModel):
    user_id: int
    pay_period_start: date_type
    pay_period_end: date_type
    base_salary: float
    allowances: float | None = 0.0
    deductions: float | None = 0.0
    net_pay: float | None = None  # Computed as base_salary + allowances - deductions when omitted
    payment_date: date_type
    status: str | None = "draft"  # draft, paid


class UpdatePaycheck(BaseModel):
    user_id: int | None = None
    pay_period_start: date_type | None = None
    pay_period_end: date_type | None = None
    base_salary: float | None = None
    allowances: float | None = None
    deductions: float | None = None
    net_pay: float | None = None
    payment_date: date_type | None = None
    status: str | None = None


@hr_router.post("/paycheck")
async def create_paycheck(new_paycheck: CreatePaycheck, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Create a new paycheck
    Args:
        new_paycheck: New paycheck information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success', 'data': paycheck}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Create paycheck for user ID: {new_paycheck.user_id} ({new_paycheck.pay_period_start} - {new_paycheck.pay_period_end})')

    try:
        user = await db.get(User, new_paycheck.user_id)
        if not user:
            log.warning(f'User ID: {new_paycheck.user_id} not found')
            return Response({"status": "fail", "error": f"User with id {new_paycheck.user_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

        if new_paycheck.pay_period_end < new_paycheck.pay_period_start:
            log.warning(f'Paycheck period end {new_paycheck.pay_period_end} is before period start {new_paycheck.pay_period_start}')
            return Response({"status": "fail", "error": "pay_period_end must not be before pay_period_start"}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')

        allowances = new_paycheck.allowances if new_paycheck.allowances is not None else 0.0
        deductions = new_paycheck.deductions if new_paycheck.deductions is not None else 0.0
        net_pay = new_paycheck.net_pay if new_paycheck.net_pay is not None else new_paycheck.base_salary + allowances - deductions

        paycheck = Paycheck(
            user_id=new_paycheck.user_id,
            pay_period_start=new_paycheck.pay_period_start,
            pay_period_end=new_paycheck.pay_period_end,
            base_salary=new_paycheck.base_salary,
            allowances=allowances,
            deductions=deductions,
            net_pay=net_pay,
            payment_date=new_paycheck.payment_date,
            status=new_paycheck.status if new_paycheck.status is not None else "draft",
        )
        db.add(paycheck)
        await db.commit()
        await db.refresh(paycheck)
        paycheck_data = paycheck.to_dict()
        log.info(f'Paycheck created: {paycheck_data}')
        return Response({"status": "success", "data": paycheck_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to create paycheck: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@hr_router.put("/paycheck/{paycheck_id}")
async def update_paycheck(paycheck_id: int, new_paycheck: UpdatePaycheck, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Update paycheck by id
    Args:
        paycheck_id: Paycheck ID to update
        new_paycheck: New paycheck information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Update paycheck ID: {paycheck_id}')

    old_paycheck = await db.get(Paycheck, paycheck_id)
    if not old_paycheck:
        log.warning(f'Paycheck ID: {paycheck_id} not found')
        return Response({"status": "fail", "error": f"Paycheck with id {paycheck_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        for field_name, field_value in new_paycheck:
            if field_value is not None:
                setattr(old_paycheck, field_name, field_value)
        if old_paycheck.pay_period_end < old_paycheck.pay_period_start:
            log.warning(f'Paycheck period end {old_paycheck.pay_period_end} is before period start {old_paycheck.pay_period_start}')
            await db.rollback()
            return Response({"status": "fail", "error": "pay_period_end must not be before pay_period_start"}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
        await db.commit()
        await db.refresh(old_paycheck)
        log.info(f'Paycheck updated: {old_paycheck.to_dict()}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to update paycheck: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@hr_router.delete("/paycheck/{paycheck_id}")
async def delete_paycheck(paycheck_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Delete paycheck by id
    Args:
        paycheck_id: Paycheck ID to delete
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('hr', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Delete paycheck ID: {paycheck_id}')

    paycheck = await db.get(Paycheck, paycheck_id)
    if not paycheck:
        log.warning(f'Paycheck ID: {paycheck_id} not found')
        return Response({"status": "fail", "error": f"Paycheck with id {paycheck_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(paycheck)
        await db.commit()
        log.info(f'Paycheck deleted ID: {paycheck_id}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to delete paycheck: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
