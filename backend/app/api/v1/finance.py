"""
Finance module, Query, add, remove and update Finance expense records
"""
from traceback import format_exc
from uuid import UUID

from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse as Response
from pydantic import BaseModel
from sqlalchemy import select
from starlette import status

from app.api.common import get_current_user, permission_check
from app.core.database import get_db
from app.core.log_module import user_log
from app.models import ExpenseType, Finance, User

finance_router = APIRouter(prefix="/finance", tags=["Finance"])


@finance_router.get("/expense_list")
async def get_expense_list(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get all finance expense records in the database.
    Args:
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified list of Finance objects
    """
    log = user_log(current_user.id)
    if not await permission_check('finance', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info('Query all expenses')
    expenses = (await db.scalars(select(Finance))).all()
    data = []
    for e in expenses:
        data.append(e.to_dict())
    log.info(f"{str(len(data))} expenses found")

    return Response({
        "status": "success",
        "data": data,
    }, status_code=status.HTTP_200_OK, media_type='application/json')


@finance_router.get("/expense/{expense_id}")
async def get_expense(expense_id: UUID, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get finance expense record by id
    Args:
        expense_id: The expense to query
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified Finance object
    """
    log = user_log(current_user.id)
    if not await permission_check('finance', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Query expense ID: {expense_id}')

    expense = await db.get(Finance, expense_id)
    if not expense:
        log.warning(f'Expense ID: {expense_id} not found')
        return Response({"status": "fail", "error": f"Expense with id {expense_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    expense_data = expense.to_dict()
    log.info(f'Query expense: {expense_data}')

    return Response({"status": "success", "data": expense_data}, status_code=status.HTTP_200_OK, media_type='application/json')


class CreateExpense(BaseModel):
    expense_type: ExpenseType


class UpdateExpense(BaseModel):
    expense_type: ExpenseType | None = None


@finance_router.post("/expense")
async def create_expense(new_expense: CreateExpense, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Create a new finance expense record
    Args:
        new_expense: New expense information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success', 'data': expense}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('finance', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Create expense with type: {new_expense.expense_type}')

    try:
        expense = Finance(expense_type=new_expense.expense_type)
        db.add(expense)
        await db.commit()
        await db.refresh(expense)
        expense_data = expense.to_dict()
        log.info(f'Expense created: {expense_data}')
        return Response({"status": "success", "data": expense_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to create expense: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@finance_router.put("/expense/{expense_id}")
async def update_expense(expense_id: UUID, new_expense: UpdateExpense, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Update finance expense record by id
    Args:
        expense_id: Expense ID to update
        new_expense: New expense information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('finance', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Update expense ID: {expense_id}')

    old_expense = await db.get(Finance, expense_id)
    if not old_expense:
        log.warning(f'Expense ID: {expense_id} not found')
        return Response({"status": "fail", "error": f"Expense with id {expense_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        for field_name, field_value in new_expense:
            if field_value is not None:
                setattr(old_expense, field_name, field_value)
        await db.commit()
        await db.refresh(old_expense)
        log.info(f'Expense updated: {old_expense.to_dict()}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to update expense: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@finance_router.delete("/expense/{expense_id}")
async def delete_expense(expense_id: UUID, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Delete finance expense record by id
    Args:
        expense_id: Expense ID to delete
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('finance', current_user.id, db):
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Delete expense ID: {expense_id}')

    expense = await db.get(Finance, expense_id)
    if not expense:
        log.warning(f'Expense ID: {expense_id} not found')
        return Response({"status": "fail", "error": f"Expense with id {expense_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(expense)
        await db.commit()
        log.info(f'Expense deleted ID: {expense_id}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to delete expense: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
