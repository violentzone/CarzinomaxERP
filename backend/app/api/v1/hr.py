"""
HR module, Query, add, remove and update User
"""
from fastapi import Depends, HTTPException, APIRouter, Response
from sqlalchemy import select
from starlette import status

from app.api.common import get_current_user
from app.models import User
from app.core.database import get_db
from app.core.log_module import user_log

hr_router = APIRouter(prefix="/hr", tags=["HR"])

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
    log = user_log(current_user)
    log.info(f'Query user ID: {user_id}')

    user = await db.get(User, user_id).to_dict()
    log.info(f'Query user: {user}')

    return Response({
        "status": "success",
        "data": user,
        status.HTTP_200_OK,
        media_type='application/json'
    })