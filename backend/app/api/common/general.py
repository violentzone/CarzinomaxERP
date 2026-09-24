"""
Shared authentication dependency for API routers
"""

from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from typing import Literal

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User
from app.core.log_module import user_log


bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the bearer token in the Authorization header to an active user.

    Args:
        credentials: Parsed ``Authorization: Bearer <token>`` header, if present.
        db: Database session, defined in app.core.database.

    Returns:
        User: The authenticated, active user.

    Raises:
        HTTPException: 401 if the header is missing, the token is invalid or expired,
            the user is unknown or inactive, or the token predates the user's last logout.
    """
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    try:
        user = await db.get(User, int(payload.sub))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        user = None
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    # Tokens issued before the user's last logout are revoked
    cutoff = user.tokens_valid_from
    if cutoff is not None and payload.iat < cutoff.timestamp():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
    return user


async def permission_check(endpoint: Literal['finance', 'scm', 'hr', 'dev'], login_user_id: int,
                     db: AsyncSession = Depends(get_db)) -> bool:
    """
    General function to check if the login user is allowed to access the API.
    Args:
        endpoint: Which functional endpoint model call check permissions.
        login_user_id: Login user id
        db: Database session, defined in app.core.database.

    Returns:
        True if permitted, False otherwise.
        Raises error is false endpoint is given
    """
    log = user_log(login_user_id)
    user = await db.get(User, int(login_user_id))
    if not user:
        # Found no current login user, shall not happen but checks everytime `permission_check` is called
        return False

    if endpoint == 'finance':
        if not user.has_finance_access:
            log.warning('User did not have finance access.')
            return False
    elif endpoint == 'scm':
        if not user.has_scm_access:
            log.warning('User did not have scm access.')
            return False
    elif endpoint == 'hr':
        if not user.has_hr_access:
            log.warning('User did not have hr access.')
            return False
    elif endpoint == 'dev':
        if not user.has_dev_access:
            log.warning('User did not have dev access.')
            return False
    else:
        # Shall not happen cus parameter already defined, but still chek
        raise ValueError('Endpoint must be either "scm" or "hr" or "dev"')
    log.info(f'User permitted with {endpoint} endpoint.')
    return True