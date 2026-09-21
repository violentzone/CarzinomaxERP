from fastapi import Depends, HTTPException, APIRouter

from app.api.common import get_current_user

hr_router = APIRouter(prefix="/hr", tags=["HR"])
