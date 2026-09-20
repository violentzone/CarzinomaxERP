from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.core.database import get_db

auth_router = APIRouter()

@auth_router.post("/login")
async def login(user_email: str, password: str, db=Depends(get_db)):
    """
    Login endpoint
    Args:
        user_email: User input Email
        password: User input Password
        db: Database connection, defined in app.core.database

    Returns:

    """