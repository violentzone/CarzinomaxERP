from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional
import jwt
from bcrypt import hashpw, gensalt, checkpw

from app.core.config import settings
from app.schemas.auth import TokenPayload

ALGORITHM = "HS256"
REQUIRED_CLAIMS = ["sub", "iat", "exp"]

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token containing the subject.

    Args:
        subject: The subject to encode in the token (typically the user ID).
        expires_delta: Optional timedelta for token expiration. Defaults to settings expiration.

    Returns:
        str: The encoded JWT access token.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # ``iat`` keeps sub-second precision (RFC 7519 allows non-integer NumericDate)
    # so it compares exactly against a user's ``tokens_valid_from`` logout cutoff.
    to_encode = {"exp": expire, "sub": str(subject), "iat": now.timestamp()}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> TokenPayload:
    """Verify an access token's signature and expiry and return its claims.

    Args:
        token: The encoded JWT string, typically taken from the Authorization header.

    Returns:
        TokenPayload: The ``sub`` (user id) and ``iat`` (issued-at) claims.

    Raises:
        jwt.InvalidTokenError: If the signature is invalid, the token has expired,
            or any required claim (sub, iat, exp) is missing.
    """
    claims = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[ALGORITHM],
        options={"require": REQUIRED_CLAIMS},
    )
    return TokenPayload(sub=claims["sub"], iat=claims["iat"])

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
