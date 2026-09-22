"""
HR module, Query, add, remove and update User
"""
from datetime import datetime

from fastapi import Depends, HTTPException, APIRouter, Response
from sqlalchemy import select
from starlette import status
from pydantic import BaseModel

from app.api.common import get_current_user
from app.models import User
from app.core.database import get_db
from app.core.log_module import user_log

hr_router = APIRouter(prefix="/hr", tags=["HR"])

@hr_router.get("/employee_list")
async def get_employee_list(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get all users in the database.
    Args:
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified list of User objects
    """
    log = user_log(current_user)
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
async def get_user(user_id: int, current_user: int, db = Depends(get_db)):
    """
    Get user by id
    Args:
        user_id: The user to query
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified user object
    """
    log = user_log(current_user)
    log.info(f'Query user ID: {user_id}')

    user = await db.get(User, user_id).to_dict()
    log.info(f'Query user: {user}')

    return Response({"status": "success", "data": user,}, status_code=status.HTTP_200_OK, media_type='application/json')


class UpdateUser(BaseModel):
    email: str | None = None
    password: str | None = None
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    has_finance_access: bool | None = None
    has_scm_access: bool | None = None
    has_hr_access: bool | None = None
    has_dev_access: bool | None = None
    tokens_valid_from: datetime | None = None

@hr_router.put("/user/{user_id}")
async def update_user(user_id: int, new_user: UpdateUser, current_user: int = Depends(get_current_user), db = Depends(get_db)):
    """
    Update user by id
    Args:
        user_id: User ID to update
        new_user: New user information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        True if user successfully updated, else False
    """
    log = user_log(current_user)
    log.info(f'Update user ID: {user_id}')
    old_user = await db.get(User, user_id)
    try:
        for field_name, field_value in new_user:
            if field_value is not None:
                setattr(old_user, field_name, field_value)
        db.commit()
        db.refresh(old_user)
        log.info(f'User updated: {old_user.to_dict()}')
        return True
    except Exception as err:
