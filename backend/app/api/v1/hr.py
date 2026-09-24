"""
HR module, Query, add, remove and update User
"""
from datetime import datetime
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
from app.models import User

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
        log.info(f'User created: {user.to_dict()}')
        return Response({"status": "success", "data": user.to_dict()}, status_code=status.HTTP_201_CREATED, media_type='application/json')
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
