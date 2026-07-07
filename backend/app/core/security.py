from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional
import jwt
from bcrypt import hashpw, gensalt, checkpw

from app.core.config import settings

ALGORITHM = "HS256"

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token containing the subject.

    Args:
        subject: The subject to encode in the token (typically the user ID).
        expires_delta: Optional timedelta for token expiration. Defaults to settings expiration.

    Returns:
        str: The encoded JWT access token.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against its hashed version.

    Args:
        plain_password: The plain text password.
        hashed_password: The hashed password string.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    try:
        return checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Hash a plain text password using bcrypt.

    Args:
        password: The plain text password to hash.

    Returns:
        str: The bcrypt hashed password string.
    """
    return hashpw(password.encode("utf-8"), gensalt()).decode("utf-8")
