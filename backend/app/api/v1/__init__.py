from fastapi import APIRouter
from app.api.v1.auth import auth_router
from app.api.v1.dev_tracking import dev_tracking_router
from app.api.v1.finance import finance_router
from app.api.v1.hr import hr_router
from app.api.v1.scm import scm_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(finance_router)
api_router.include_router(hr_router)
api_router.include_router(scm_router)
api_router.include_router(dev_tracking_router)
