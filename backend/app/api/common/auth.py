"""
Shared authentication dependency for API routers
"""

from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User

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
