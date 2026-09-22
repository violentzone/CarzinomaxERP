"""
Authorization endpoints
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app import models
from app.api.common import get_current_user
from app.core import security
from app.core.database import get_db
from app.core.log_module import system_log, user_log
from app.core.security import create_access_token
from app.models import User
from app.schemas import UserResponse

auth_router = APIRouter(prefix="/auth", tags=["auth"])

@auth_router.post("/login")
async def login(user_email: str, password: str, db=Depends(get_db)):
    """
    Login endpoint
    Args:
        user_email: User input Email
        password: User input Password
        db: Database connection, defined in app.core.database

    Returns:
        A JWT token to be used as Authorization header
    """
    act_log = system_log()
    act_log.info(f'Attempting to log in with email: {user_email}')
    user = await db.scalar(select(models.User).filter(models.User.email == user_email))

    # Found no user email
    if not user:
        act_log.warning(f'User with email {user_email} does not exist')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    if not security.verify_password(password, user.hashed_password):
        act_log.warning(f'Incorrect password')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    act_log.info(f'Login Successful, user: {str(user.id)}')
    return Response(create_access_token(user.id), media_type="application/json", status_code=200)

@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Logout endpoint
    JWTs are stateless (nothing is stored server-side), so "removing" a token
    means recording a cutoff on the user: every access token issued before now
    is rejected by get_current_user, on every device. Tokens issued by a later
    login are unaffected.
    Args:
        current_user: The user resolved from the Authorization: Bearer header
        db: Database connection, defined in app.core.database
    """
    current_user.tokens_valid_from = datetime.now(timezone.utc)
    await db.commit()
    user_log(current_user.id).info("Logged out; access tokens issued before now are revoked")

@auth_router.get("/me")
async def me(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current user
    Args:
        current_user: The user resolved from the Authorization: Bearer header

    Returns:
        The signed-in user, serialized as UserResponse
    """
    calling_user = await get_current_user()
    data = calling_user.to_dict()
    return Response({
        'status': 'success',
        'data': data
    }, status_code=status.HTTP_200_OK, media_type='application/json')