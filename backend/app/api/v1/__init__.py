from fastapi import APIRouter
from app.api.v1.auth import auth_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])