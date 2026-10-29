"""
Finance module, Query, add, remove and update Finance expense records
"""
import asyncio
from datetime import date
from pathlib import PurePosixPath
from traceback import format_exc
from uuid import UUID

from fastapi import Depends, APIRouter, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from starlette import status

from app.api.common import get_current_user, permission_check
from app.core.database import get_db
from app.core.log_module import user_log
from app.core.receipts import extract_receipt
from app.core.uploads import MIME_BY_EXTENSION, UPLOAD_ROOT, attachment_path, load_attachment, save_attachment
from app.models import DevProject, ExpenseCategory, ExpenseType, Finance, ExpenseStatus, User

finance_router = APIRouter(prefix="/finance", tags=["Finance"])


@finance_router.get("/expense_list")
async def get_expense_list(start_date: date | None = None, end_date: date | None = None, expense_type: ExpenseType | None = None, category: ExpenseCategory | None = None, payment_status: ExpenseStatus | None = None, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get finance expense records in the database, filtered by the query parameters that are given
    Args:
        start_date: Earliest `expense_date` to include (inclusive), None for no lower bound
        end_date: Latest `expense_date` to include (inclusive), None for no upper bound
        expense_type: Only expenses of this type, None for all types
        category: Only expenses in this category, None for all categories
        payment_status: Only expenses with this payment status (`paid`, `unpaid`, `overdue`), None for all
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified list of Finance objects
    """
    log = user_log(current_user.id)
    if not await permission_check('finance', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[EXPENSE] Query expenses with start_date={start_date}, end_date={end_date}, expense_type={expense_type}, category={category}, payment_status={payment_status}')
    stmt = select(Finance)
    if start_date is not None:
        stmt = stmt.where(Finance.expense_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(Finance.expense_date <= end_date)
    if expense_type is not None:
        stmt = stmt.where(Finance.expense_type == expense_type)
    if category is not None:
        stmt = stmt.where(Finance.category == category)
    if payment_status is not None:
        stmt = stmt.where(Finance.status == payment_status)
    expenses = (await db.scalars(stmt)).all()
    data = []
    for e in expenses:
        data.append(e.to_dict())
    log.info(f"[EXPENSE] {str(len(data))} expenses found")

    return JSONResponse({
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
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[EXPENSE] Query expense ID: {expense_id}')

    expense = await db.get(Finance, expense_id)
    if not expense:
        log.warning(f'[EXPENSE] Expense ID: {expense_id} not found')
        return JSONResponse({"status": "fail", "error": f"Expense with id {expense_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    expense_data = expense.to_dict()
    log.info(f'[EXPENSE] Query expense: {expense_data}')

    return JSONResponse({"status": "success", "data": expense_data}, status_code=status.HTTP_200_OK, media_type='application/json')


@finance_router.get("/expense/{expense_id}/receipt")
async def get_expense_receipt(expense_id: UUID, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Serve the receipt or invoice an expense was booked from, as the stored file (JPEG or PDF) instead of the JSON envelope
    Args:
        expense_id: The expense whose receipt to serve
        current_user: Signed in user; any user with finance access may view the receipt of any expense because the ledger is shared
        db: Database session(Created by `get_db`)

    Returns:
        The file with its media type and `Content-Disposition: inline` on success, {'status': 'fail', 'error': error message} otherwise
    """
    log = user_log(current_user.id)
    if not await permission_check('finance', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[RECEIPT] Query receipt of expense ID: {expense_id}')

    expense = await db.get(Finance, expense_id)
    if not expense:
        log.warning(f'[RECEIPT] Expense ID: {expense_id} not found')
        return JSONResponse({"status": "fail", "error": f"Expense with id {expense_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')
    if not expense.receipt_path:
        log.warning(f'[RECEIPT] Expense ID: {expense_id} has no receipt')
        return JSONResponse({"status": "fail", "error": f"Expense with id {expense_id} has no receipt"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        # receipt_path is only ever a stored attachment resolved under UPLOAD_ROOT (REST: the caller's own, chat tool: any uploader's by uuid), so the containment check is belt and braces
        path = (UPLOAD_ROOT / expense.receipt_path).resolve()
        media_type = MIME_BY_EXTENSION.get(path.suffix.lstrip('.'))
        if not path.is_relative_to(UPLOAD_ROOT.resolve()):
            log.warning(f'[RECEIPT] Receipt path {expense.receipt_path} of expense {expense_id} points outside the upload directory')
            return JSONResponse({"status": "fail", "error": "Receipt file is missing"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')
        if not path.is_file() or media_type is None:
            log.warning(f'[RECEIPT] Receipt file {expense.receipt_path} of expense {expense_id} is missing or has an unknown type')
            return JSONResponse({"status": "fail", "error": "Receipt file is missing"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')
        log.info(f'[RECEIPT] Serves receipt {expense.receipt_path} of expense {expense_id}')
        response = FileResponse(path, media_type=media_type, headers={'Content-Disposition': f'inline; filename="receipt-{expense_id}{path.suffix}"'})
        return response
    except Exception as err:
        log.error(f'[RECEIPT] Failed to serve receipt of expense {expense_id}: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


class CreateExpense(BaseModel):
    expense_type: ExpenseType
    amount: float
    vendor: str | None = None
    reference: str | None = None
    description: str | None = None
    category: ExpenseCategory | None = None
    expense_date: date = Field(default_factory=date.today)  # document date, today when recorded by hand
    due_date: date | None = None
    paid_date: date | None = None
    project_id: int | None = None
    receipt_path: str | None = None  # `receipt_path` returned by POST /finance/receipt


# Optional columns the ledger form may clear by sending an explicit null (the other routers ignore nulls)
CLEARABLE_EXPENSE_FIELDS = ('vendor', 'reference', 'description', 'category', 'due_date', 'paid_date', 'project_id')


class UpdateExpense(BaseModel):
    expense_type: ExpenseType | None = None
    amount: float | None = None
    vendor: str | None = None
    reference: str | None = None
    description: str | None = None
    category: ExpenseCategory | None = None
    expense_date: date | None = None
    due_date: date | None = None
    paid_date: date | None = None
    project_id: int | None = None


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
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[EXPENSE] Create expense with type: {new_expense.expense_type}')

    try:
        if new_expense.project_id is not None and not await db.get(DevProject, new_expense.project_id):
            log.warning(f'[EXPENSE] Dev project ID: {new_expense.project_id} not found')
            return JSONResponse({"status": "fail", "error": f"Dev project with id {new_expense.project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')
        expense = Finance(**new_expense.model_dump(exclude_none=True))
        if expense.paid_date is not None:
            expense.status = ExpenseStatus.PAID
        elif expense.due_date is not None and expense.due_date < date.today():
            expense.status = ExpenseStatus.OVERDUE
        else:
            expense.status = ExpenseStatus.UNPAID
        if new_expense.receipt_path is not None:
            # Only a file POST /finance/receipt stored for this caller may be linked, and it is stored by its canonical "<user_id>/<uuid>.<ext>" path
            parts = PurePosixPath(new_expense.receipt_path).parts
            if len(parts) != 2 or parts[0] != str(current_user.id):
                raise ValueError(f'Unknown receipt {new_expense.receipt_path}')
            expense.receipt_path = attachment_path(current_user.id, PurePosixPath(parts[1]).stem).relative_to(UPLOAD_ROOT).as_posix()
        db.add(expense)
        await db.commit()
        await db.refresh(expense)
        expense_data = expense.to_dict()
        log.info(f'[EXPENSE] Expense created: {expense_data}')
        return JSONResponse({"status": "success", "data": expense_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'[EXPENSE] Failed to create expense: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


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
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[EXPENSE] Update expense ID: {expense_id}')

    old_expense = await db.get(Finance, expense_id)
    if not old_expense:
        log.warning(f'[EXPENSE] Expense ID: {expense_id} not found')
        return JSONResponse({"status": "fail", "error": f"Expense with id {expense_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        if new_expense.project_id is not None and not await db.get(DevProject, new_expense.project_id):
            log.warning(f'[EXPENSE] Dev project ID: {new_expense.project_id} not found')
            return JSONResponse({"status": "fail", "error": f"Dev project with id {new_expense.project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')
        for field_name, field_value in new_expense:
            # A null that was sent on purpose clears a clearable field, e.g. re-opening a bill by clearing paid_date
            if field_value is not None or (field_name in CLEARABLE_EXPENSE_FIELDS and field_name in new_expense.model_fields_set):
                setattr(old_expense, field_name, field_value)
        if old_expense.paid_date is not None:
            old_expense.status = ExpenseStatus.PAID
        elif old_expense.due_date is not None and old_expense.due_date < date.today():
            old_expense.status = ExpenseStatus.OVERDUE
        else:
            old_expense.status = ExpenseStatus.UNPAID
        await db.commit()
        await db.refresh(old_expense)
        log.info(f'[EXPENSE] Expense updated: {old_expense.to_dict()}')
        return JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'[EXPENSE] Failed to update expense: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


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
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[EXPENSE] Delete expense ID: {expense_id}')

    expense = await db.get(Finance, expense_id)
    if not expense:
        log.warning(f'[EXPENSE] Expense ID: {expense_id} not found')
        return JSONResponse({"status": "fail", "error": f"Expense with id {expense_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(expense)
        await db.commit()
        log.info(f'[EXPENSE] Expense deleted ID: {expense_id}')
        return JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'[EXPENSE] Failed to delete expense: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@finance_router.post("/receipt")
async def read_receipt(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Store one receipt or invoice (PNG, JPEG, WebP or PDF) and read it into an expense draft; nothing is booked until the client posts the draft to `POST /finance/expense`
    Args:
        file: Multipart field `file`; the type is sniffed from the bytes, the declared content type is ignored
        current_user: Signed in user, the file is stored under the caller's upload directory
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success', 'data': {'receipt_path': path, 'draft': draft | None, 'note': why the draft is None}}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('finance', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[RECEIPT] Reads receipt {file.filename} ({file.content_type}, {file.size} bytes)')

    try:
        attachment = await save_attachment(current_user.id, file)
    except ValueError as err:
        log.warning(f'[RECEIPT] Receipt rejected: {err}')
        return JSONResponse({"status": "fail", "error": str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
    except Exception:
        log.error(f'[RECEIPT] Failed to store receipt: {format_exc()}')
        return JSONResponse({"status": "fail", "error": "Could not store the receipt"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, media_type='application/json')

    # The file is stored whatever the model does, so the user can still book by hand with the receipt attached
    receipt_path = attachment_path(current_user.id, attachment.id).relative_to(UPLOAD_ROOT).as_posix()
    projects = (await db.execute(select(DevProject.project_id, DevProject.project_name))).all()
    try:
        loaded = await asyncio.to_thread(load_attachment, current_user.id, attachment.id)
        draft = await extract_receipt(loaded, [name for _, name in projects])
    except ValueError as err:
        log.warning(f'[RECEIPT] Receipt {receipt_path} not readable: {err}')
        response = JSONResponse({"status": "success", "data": {'receipt_path': receipt_path, 'draft': None, 'note': str(err)}}, status_code=status.HTTP_200_OK, media_type='application/json')
        return response
    except Exception:
        log.error(f'[RECEIPT] Failed to read receipt {receipt_path}: {format_exc()}')
        response = JSONResponse({"status": "success", "data": {'receipt_path': receipt_path, 'draft': None, 'note': 'The model could not be reached, fill in the expense by hand'}}, status_code=status.HTTP_200_OK, media_type='application/json')
        return response

    # The model returns a project name from the list it was given; the client needs the id
    wanted = (draft.project_name or '').strip().casefold()
    project_id = next((pid for pid, name in projects if wanted and name.strip().casefold() == wanted), None)
    receipt_data = {'receipt_path': receipt_path, 'draft': {**draft.model_dump(), 'project_id': project_id}, 'note': None}
    log.info(f'[RECEIPT] Receipt read: {receipt_data}')
    response = JSONResponse({"status": "success", "data": receipt_data}, status_code=status.HTTP_200_OK, media_type='application/json')
    return response
