from langchain.tools import tool
from pydantic import BaseModel
from sqlalchemy import select
from datetime import datetime, date as date_type
from typing import Literal
from uuid import UUID

from app.core.database import SessionLocal
from app.models.auth import User
from app.models.dev_tracking import DevInvestment, DevProject
from app.models.finance import ExpenseType, Finance
from app.models.hr import AttendanceLog


class UserInfo(BaseModel):
    id: int | None = None
    full_name: str | None = None
    email: str | None = None
    is_active: bool | None = None
    has_finance_access: bool | None = None
    has_scm_access: bool | None = None
    has_hr_access: bool | None = None
    has_dev_access: bool | None = None

class GetUserOutput(BaseModel):
    data: list[UserInfo] = []
    message: str | None = None

@tool
async def get_user_info(
    user_id: int,
    target_user_id: int | None = None,
    target_user_name: str | None = None,
    has_finance_access: bool | None = None,
    has_scm_access: bool | None = None,
    has_hr_access: bool | None = None,
    has_dev_access: bool | None = None,
) -> GetUserOutput:
    """
    Gets user information with the permission of user_id, from database table "user", filtered by parameters that is not None
    Args:
        user_id: User who call this tool
        target_user_id: Target user ID to query, None if not filter by ID
        target_user_name: Target username, None if not filter by name
        has_finance_access: Filter user with finance access, None if do not want to filter by finance access
        has_scm_access: Filter user with SCM access, None if do not want to filter by SCM access
        has_hr_access: Filter user with HR access, None if do not want to filter by HR access
        has_dev_access: Filter user with dev access, None if do not want to filter by dev access

    Returns:
        Every user that fits the condition listed in `GetUserOutput.data`, all users if no filter given, empty list with the reason in `message` if no user fits
    """
    stmt = select(User)
    if target_user_id is not None:
        stmt = stmt.where(User.id == target_user_id)
    if target_user_name is not None:
        stmt = stmt.where(User.full_name == target_user_name)
    if has_finance_access is not None:
        stmt = stmt.where(User.has_finance_access == has_finance_access)
    if has_scm_access is not None:
        stmt = stmt.where(User.has_scm_access == has_scm_access)
    if has_hr_access is not None:
        stmt = stmt.where(User.has_hr_access == has_hr_access)
    if has_dev_access is not None:
        stmt = stmt.where(User.has_dev_access == has_dev_access)

    async with SessionLocal() as session:
        users = (await session.execute(stmt)).scalars().all()

    if not users:
        return GetUserOutput(data=[], message='No user fits the condition')
    return GetUserOutput(data=[UserInfo.model_validate(u, from_attributes=True) for u in users])

class ExpenseDetail(BaseModel):
    id: UUID
    expense_type: ExpenseType
    amount: float
    created_at: datetime
    updated_at: datetime

class GetExpensesOutput(BaseModel):
    expense_detail: list[ExpenseDetail]
    total: float

@tool
async def get_expenses(
    user_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    expense_type: Literal["paycheck", "petty_cash", "investment", "other"] | None = None,
) -> GetExpensesOutput | None:
    """
    Get expenses data with the permission of user_id, from database table "finance", filtered by parameters that is not None
    Args:
        user_id: User who call this tool
        start_date: Start period to query expenses (inclusive, by created_at), None if not filter by start date
        end_date: End period to query expenses (inclusive, by created_at), None if not filter by end date
        expense_type: Specify which type of expenses to filter by, None if not filter by type

    Returns:
        Expenses data, each expense listed in `GetExpensesOutput.expense_detail` with summed amount in `total`, None if no expenses found with filter given
    """
    stmt = select(Finance)
    if start_date is not None:
        stmt = stmt.where(Finance.created_at >= start_date)
    if end_date is not None:
        stmt = stmt.where(Finance.created_at <= end_date)
    if expense_type is not None:
        stmt = stmt.where(Finance.expense_type == ExpenseType(expense_type))

    async with SessionLocal() as session:
        expenses = (await session.execute(stmt)).scalars().all()

    if not expenses:
        return None
    total = float(sum(e.amount for e in expenses))
    return GetExpensesOutput(
        expense_detail=[ExpenseDetail.model_validate(e, from_attributes=True) for e in expenses],
        total=total,
    )

@tool
async def create_expense(
    user_id: int,
    expense_type: Literal["paycheck", "petty_cash", "investment", "other"],
    amount: float,
) -> ExpenseDetail:
    """
    Creates a new expense record with the permission of user_id, into database table "finance"
    Args:
        user_id: User who call this tool
        expense_type: Type of the expense to create
        amount: Amount of the expense to create

    Returns:
        The created expense record
    """
    expense = Finance(expense_type=ExpenseType(expense_type), amount=amount)

    async with SessionLocal() as session:
        session.add(expense)
        await session.commit()
        await session.refresh(expense)

    return ExpenseDetail.model_validate(expense, from_attributes=True)

class DevProjectDetail(BaseModel):
    project_id: int
    project_name: str
    project_description: str | None
    created_at: datetime
    updated_at: datetime

class GetDevProjectOutput(BaseModel):
    project_detail: list[DevProjectDetail]
    total: int

@tool
async def get_dev_project(
    user_id: int,
    project_id: int | None = None,
    project_name: str | None = None,
) -> GetDevProjectOutput | None:
    """
    Gets dev project information with the permission of user_id, from database table "dev_projects", filtered by parameters that is not None
    Args:
        user_id: User who call this tool
        project_id: Target project ID to query, None if not filter by ID
        project_name: Target project name to query, None if not filter by name

    Returns:
        Dev project data, each project listed in `GetDevProjectOutput.project_detail` with count in `total`, None if no project fits condition
    """
    stmt = select(DevProject)
    if project_id is not None:
        stmt = stmt.where(DevProject.project_id == project_id)
    if project_name is not None:
        stmt = stmt.where(DevProject.project_name == project_name)

    async with SessionLocal() as session:
        projects = (await session.execute(stmt)).scalars().all()

    if not projects:
        return None
    return GetDevProjectOutput(
        project_detail=[DevProjectDetail.model_validate(p, from_attributes=True) for p in projects],
        total=len(projects),
    )

class DevInvestmentDetail(BaseModel):
    id: int
    date: date_type
    project_id: int
    amount: float
    vendor: str | None
    category: str
    description: str | None
    created_at: datetime
    updated_at: datetime

class GetDevInvestmentOutput(BaseModel):
    investment_detail: list[DevInvestmentDetail]
    total: float

@tool
async def get_dev_investment(
    user_id: int,
    project_id: int | None = None,
    start_date: date_type | None = None,
    end_date: date_type | None = None,
    vendor: str | None = None,
    category: str | None = None,
) -> GetDevInvestmentOutput | None:
    """
    Gets dev investment data with the permission of user_id, from database table "dev_investments", filtered by parameters that is not None
    Args:
        user_id: User who call this tool
        project_id: Project ID the investments belong to, None if not filter by project
        start_date: Start period to query investments (inclusive, by date), None if not filter by start date
        end_date: End period to query investments (inclusive, by date), None if not filter by end date
        vendor: Vendor of the investments (e.g. AWS, GCP, Vercel), None if not filter by vendor
        category: Category of the investments (e.g. cloud, software_licenses, hardware, consulting), None if not filter by category

    Returns:
        Dev investment data, each investment listed in `GetDevInvestmentOutput.investment_detail` with summed amount in `total`, None if no investments found with filter given
    """
    stmt = select(DevInvestment)
    if project_id is not None:
        stmt = stmt.where(DevInvestment.project_id == project_id)
    if start_date is not None:
        stmt = stmt.where(DevInvestment.date >= start_date)
    if end_date is not None:
        stmt = stmt.where(DevInvestment.date <= end_date)
    if vendor is not None:
        stmt = stmt.where(DevInvestment.vendor == vendor)
    if category is not None:
        stmt = stmt.where(DevInvestment.category == category)

    async with SessionLocal() as session:
        investments = (await session.execute(stmt)).scalars().all()

    if not investments:
        return None
    total = float(sum(i.amount for i in investments))
    return GetDevInvestmentOutput(
        investment_detail=[DevInvestmentDetail.model_validate(i, from_attributes=True) for i in investments],
        total=total,
    )

class UserAttendanceDetail(BaseModel):
    user_id: int
    date: date_type
    clocked_in: datetime
    clocked_out: datetime
    hours: float

class GetAttendanceOutput(BaseModel):
    user_detail: list[UserAttendanceDetail]
    total_hours: float

@tool
async def get_attendance(user_id: int, start_date: datetime, end_date: datetime) -> GetAttendanceOutput:
    """
    Get all attendance log in provided duration
    Args:
        user_id:  User who call this tool
        start_date: Start period to query attendance (inclusive, by date)
        end_date:  End period to query attendance (inclusive, by date)

    Returns:
        Attendance log of all users in provided duration, each user/day data listed in `GetAttendanceOutput.user_detail`
    """
    stmt = select(AttendanceLog)
    stmt = stmt.where(AttendanceLog.date >= start_date.date())
    stmt = stmt.where(AttendanceLog.date <= end_date.date())
    stmt = stmt.where(AttendanceLog.clock_out.is_not(None))

    async with SessionLocal() as session:
        logs = (await session.execute(stmt)).scalars().all()

    user_detail = [
        UserAttendanceDetail(
            user_id=a.user_id,
            date=a.date,
            clocked_in=a.clock_in,
            clocked_out=a.clock_out,
            hours=float(a.total_hours) if a.total_hours is not None else (a.clock_out - a.clock_in).total_seconds() / 3600,
        )
        for a in logs
    ]
    return GetAttendanceOutput(
        user_detail=user_detail,
        total_hours=sum(d.hours for d in user_detail),
    )
