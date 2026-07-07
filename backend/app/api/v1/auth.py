from datetime import timedelta
from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_active_user, RoleChecker
from app.models.auth import User
from app.schemas.auth import Token, UserCreate, UserResponse

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_access_token(
    db: Annotated[AsyncSession, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests.

    Args:
        db: The database session dependency.
        form_data: The login form data containing username (email) and password.

    Returns:
        Any: An object containing the generated access token and token type.

    Raises:
        HTTPException: If credentials are incorrect or the user is inactive.
    """
    # Query user by email
    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        token_type="bearer",
    )

@router.post(
    "/register",
    response_model=UserResponse,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
async def register_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_in: UserCreate
) -> Any:
    """Create a new user in the system (admin only).

    Requires an authenticated admin. This prevents unauthenticated callers
    from self-registering and assigning themselves a privileged role.

    Args:
        db: The database session dependency.
        user_in: The user creation payload.

    Returns:
        Any: The newly created User object.

    Raises:
        HTTPException: If the caller is not an admin, or if a user with the
            same email already exists.
    """
    # Check if user already exists
    result = await db.execute(select(User).filter(User.email == user_in.email))
    user = result.scalar_one_or_none()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
        
    db_user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
        is_active=True,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.get("/me", response_model=UserResponse)
async def read_user_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> Any:
    """Get the profile of the currently logged-in user.

    Args:
        current_user: The authenticated current user.

    Returns:
        Any: The current user details.
    """
    return current_user
