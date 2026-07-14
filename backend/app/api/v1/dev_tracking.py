from typing import Annotated, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db, RoleChecker
from app.models.dev_tracking import DevInvestment, DevWorkerPaycheck, ProjectDownload
from app.schemas.dev_tracking import (
    DevInvestmentCreate, DevInvestmentResponse,
    DevWorkerPaycheckCreate, DevWorkerPaycheckResponse,
    ProjectDownloadCreate, ProjectDownloadResponse,
)

router = APIRouter(dependencies=[Depends(RoleChecker(["developer", "admin"]))])

# --- Investments ---
@router.post("/investments", response_model=DevInvestmentResponse)
async def create_investment(
    db: Annotated[AsyncSession, Depends(get_db)],
    investment_in: DevInvestmentCreate
) -> Any:
    """Create a new development cloud services investment log.

    Args:
        db: The database session dependency.
        investment_in: The investment details.

    Returns:
        Any: The created DevInvestment database instance.
    """
    db_inv = DevInvestment(**investment_in.model_dump())
    db.add(db_inv)
    await db.commit()
    await db.refresh(db_inv)
    return db_inv

@router.get("/investments", response_model=List[DevInvestmentResponse])
async def list_investments(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100
) -> Any:
    """List development cloud services investments.

    Args:
        db: The database session dependency.
        skip: The number of records to skip (for pagination).
        limit: The maximum number of records to return.

    Returns:
        Any: A list of DevInvestment database instances.
    """
    result = await db.execute(select(DevInvestment).offset(skip).limit(limit))
    return result.scalars().all()

# --- Worker Paychecks ---
@router.post("/worker-paychecks", response_model=DevWorkerPaycheckResponse)
async def create_worker_paycheck(
    db: Annotated[AsyncSession, Depends(get_db)],
    paycheck_in: DevWorkerPaycheckCreate
) -> Any:
    """Record a development worker paycheck or cost.

    Args:
        db: The database session dependency.
        paycheck_in: The paycheck details.

    Returns:
        Any: The created DevWorkerPaycheck database instance.
    """
    db_pay = DevWorkerPaycheck(**paycheck_in.model_dump())
    db.add(db_pay)
    await db.commit()
    await db.refresh(db_pay)
    return db_pay

@router.get("/worker-paychecks", response_model=List[DevWorkerPaycheckResponse])
async def list_worker_paychecks(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100
) -> Any:
    """List development worker paychecks.

    Args:
        db: The database session dependency.
        skip: The number of records to skip (for pagination).
        limit: The maximum number of records to return.

    Returns:
        Any: A list of DevWorkerPaycheck database instances.
    """
    result = await db.execute(select(DevWorkerPaycheck).offset(skip).limit(limit))
    return result.scalars().all()

# --- Downloads ---
@router.post("/downloads", response_model=ProjectDownloadResponse)
async def create_download_log(
    db: Annotated[AsyncSession, Depends(get_db)],
    download_in: ProjectDownloadCreate
) -> Any:
    """Create a project download log (e.g. GitHub downloads).

    Args:
        db: The database session dependency.
        download_in: The download log details.

    Returns:
        Any: The created ProjectDownload database instance.
    """
    db_dl = ProjectDownload(**download_in.model_dump())
    db.add(db_dl)
    await db.commit()
    await db.refresh(db_dl)
    return db_dl

@router.get("/downloads", response_model=List[ProjectDownloadResponse])
async def list_downloads(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100
) -> Any:
    """List project download log counts.

    Args:
        db: The database session dependency.
        skip: The number of records to skip (for pagination).
        limit: The maximum number of records to return.

    Returns:
        Any: A list of ProjectDownload database instances.
    """
    result = await db.execute(
        select(ProjectDownload)
        .order_by(ProjectDownload.date.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
