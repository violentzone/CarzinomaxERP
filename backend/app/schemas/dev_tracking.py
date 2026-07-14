from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict
from decimal import Decimal

# Dev Investment
class DevInvestmentBase(BaseModel):
    date: date
    amount: Decimal
    vendor: str
    category: str = "cloud"
    description: Optional[str] = None

class DevInvestmentCreate(DevInvestmentBase):
    pass

class DevInvestmentResponse(DevInvestmentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Dev Worker Paycheck
class DevWorkerPaycheckBase(BaseModel):
    worker_name: str
    role: str
    payment_date: date
    amount: Decimal
    description: Optional[str] = None

class DevWorkerPaycheckCreate(DevWorkerPaycheckBase):
    pass

class DevWorkerPaycheckResponse(DevWorkerPaycheckBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Project Download
class ProjectDownloadBase(BaseModel):
    date: date
    platform: str = "github"
    download_count: int = 0
    star_count: Optional[int] = None

class ProjectDownloadCreate(ProjectDownloadBase):
    pass

class ProjectDownloadResponse(ProjectDownloadBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
