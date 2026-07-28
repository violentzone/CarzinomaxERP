
from typing import Annotated, List
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import ALGORITHM
from app.models.auth import User
from app.schemas.auth import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(reusable_oauth2)]
) -> User:
    """Retrieve the current user from the JWT access token.

    Args:
        db: The database session dependency.
        token: The OAuth2 access token.

    Returns:
        User: The authenticated user instance.

    Raises:
        HTTPException: If credentials cannot be validated or the user is not found.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (jwt.InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    if not token_data.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
        
    result = await db.execute(select(User).filter(User.id == int(token_data.sub)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Ensure the authenticated user is currently active.

    Args:
        current_user: The authenticated user instance.

    Returns:
        User: The authenticated user instance if active.

    Raises:
        HTTPException: If the user is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

class RoleChecker:
    """Dependency helper to verify if the user has specific roles."""

    def __init__(self, allowed_roles: List[str]):
        """Initialize the RoleChecker with allowed roles.

        Args:
            allowed_roles: A list of role names allowed to access the resource.
        """
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        """Call method to execute the role validation logic.

        Args:
            current_user: The current active user.

        Returns:
            User: The validated user.

        Raises:
            HTTPException: If the user is not an admin and does not have any allowed role.
        """
        has_access = False
        for r in self.allowed_roles:
            if r == "finance" and getattr(current_user, "has_finance_access", False):
                has_access = True
            elif r == "scm" and getattr(current_user, "has_scm_access", False):
                has_access = True
            elif r == "hr" and getattr(current_user, "has_hr_access", False):
                has_access = True
            elif r == "developer" and getattr(current_user, "has_dev_access", False):
                has_access = True
            elif r == current_user.role:
                has_access = True

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return current_user
