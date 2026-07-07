from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.finance import router as finance_router
from app.api.v1.scm import router as scm_router
from app.api.v1.hr import router as hr_router
from app.api.v1.dev_tracking import router as dev_tracking_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(finance_router, prefix="/finance", tags=["finance"])
api_router.include_router(scm_router, prefix="/scm", tags=["scm"])
api_router.include_router(hr_router, prefix="/hr", tags=["hr"])
api_router.include_router(dev_tracking_router, prefix="/dev-tracking", tags=["dev-tracking"])
