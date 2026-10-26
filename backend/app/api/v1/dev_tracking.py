"""
Dev tracking module, Query, add, remove and update DevProject, DevInvestment, ProjectDownload and GithubRepo
(tracked repos whose stars / release downloads are pulled when added and refreshed by the scheduler and POST /github_sync)
"""
from datetime import date as date_type
from decimal import Decimal
from traceback import format_exc

from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.api.common import get_current_user, permission_check
from app.core.database import get_db
from app.core.github import parse_repo_full_name, sync_github_repos
from app.core.log_module import user_log
from app.models import DevInvestment, DevProject, GithubRepo, ProjectDownload, User

dev_tracking_router = APIRouter(prefix="/dev_tracking", tags=["Dev Tracking"])


@dev_tracking_router.get("/project_list")
async def get_project_list(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get all dev projects in the database.
    Args:
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified list of DevProject objects
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info('[PROJECT] Query all dev projects')
    projects = (await db.scalars(select(DevProject))).all()
    data = []
    for p in projects:
        data.append(p.to_dict())
    log.info(f"[PROJECT] {str(len(data))} dev projects found")

    return JSONResponse({
        "status": "success",
        "data": data,
    }, status_code=status.HTTP_200_OK, media_type='application/json')


@dev_tracking_router.get("/project/{project_id}")
async def get_project(project_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get dev project by id
    Args:
        project_id: The dev project to query
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified DevProject object
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[PROJECT] Query dev project ID: {project_id}')

    project = await db.get(DevProject, project_id)
    if not project:
        log.warning(f'[PROJECT] Dev project ID: {project_id} not found')
        return JSONResponse({"status": "fail", "error": f"Project with id {project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    project_data = project.to_dict()
    log.info(f'[PROJECT] Query dev project: {project_data}')

    return JSONResponse({"status": "success", "data": project_data}, status_code=status.HTTP_200_OK, media_type='application/json')


class CreateProject(BaseModel):
    project_name: str
    project_description: str | None = None


class UpdateProject(BaseModel):
    project_name: str | None = None
    project_description: str | None = None


@dev_tracking_router.post("/project")
async def create_project(new_project: CreateProject, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Create a new dev project
    Args:
        new_project: New dev project information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success', 'data': project}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[PROJECT] Create dev project with name: {new_project.project_name}')

    try:
        project = DevProject(
            project_name=new_project.project_name,
            project_description=new_project.project_description,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        project_data = project.to_dict()
        log.info(f'[PROJECT] Dev project created: {project_data}')
        return JSONResponse({"status": "success", "data": project_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'[PROJECT] Failed to create dev project: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@dev_tracking_router.put("/project/{project_id}")
async def update_project(project_id: int, new_project: UpdateProject, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Update dev project by id
    Args:
        project_id: Dev project ID to update
        new_project: New dev project information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[PROJECT] Update dev project ID: {project_id}')

    old_project = await db.get(DevProject, project_id)
    if not old_project:
        log.warning(f'[PROJECT] Dev project ID: {project_id} not found')
        return JSONResponse({"status": "fail", "error": f"Project with id {project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        for field_name, field_value in new_project:
            if field_value is not None:
                setattr(old_project, field_name, field_value)
        await db.commit()
        await db.refresh(old_project)
        log.info(f'[PROJECT] Dev project updated: {old_project.to_dict()}')
        return JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'[PROJECT] Failed to update dev project: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@dev_tracking_router.delete("/project/{project_id}")
async def delete_project(project_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Delete dev project by id
    Args:
        project_id: Dev project ID to delete
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[PROJECT] Delete dev project ID: {project_id}')

    project = await db.get(DevProject, project_id)
    if not project:
        log.warning(f'[PROJECT] Dev project ID: {project_id} not found')
        return JSONResponse({"status": "fail", "error": f"Project with id {project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(project)
        await db.commit()
        log.info(f'[PROJECT] Dev project deleted ID: {project_id}')
        return JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'[PROJECT] Failed to delete dev project: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


# ---------------------------------------------------------------------------
# DevInvestment
# ---------------------------------------------------------------------------

@dev_tracking_router.get("/investment_list")
async def get_investment_list(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get all dev investments in the database.
    Args:
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified list of DevInvestment objects
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info('[INVESTMENT] Query all dev investments')
    investments = (await db.scalars(select(DevInvestment))).all()
    data = []
    for i in investments:
        data.append(i.to_dict())
    log.info(f"[INVESTMENT] {str(len(data))} dev investments found")

    return JSONResponse({
        "status": "success",
        "data": data,
    }, status_code=status.HTTP_200_OK, media_type='application/json')


@dev_tracking_router.get("/investment/{investment_id}")
async def get_investment(investment_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get dev investment by id
    Args:
        investment_id: The dev investment to query
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified DevInvestment object
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[INVESTMENT] Query dev investment ID: {investment_id}')

    investment = await db.get(DevInvestment, investment_id)
    if not investment:
        log.warning(f'[INVESTMENT] Dev investment ID: {investment_id} not found')
        return JSONResponse({"status": "fail", "error": f"Investment with id {investment_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    investment_data = investment.to_dict()
    log.info(f'[INVESTMENT] Query dev investment: {investment_data}')

    return JSONResponse({"status": "success", "data": investment_data}, status_code=status.HTTP_200_OK, media_type='application/json')


class CreateInvestment(BaseModel):
    project_id: int
    amount: Decimal
    vendor: str | None = None
    category: str | None = "cloud"
    description: str | None = None
    date: date_type


class UpdateInvestment(BaseModel):
    project_id: int | None = None
    amount: Decimal | None = None
    vendor: str | None = None
    category: str | None = None
    description: str | None = None
    date: date_type | None = None


@dev_tracking_router.post("/investment")
async def create_investment(new_investment: CreateInvestment, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Create a new dev investment
    Args:
        new_investment: New dev investment information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success', 'data': investment}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[INVESTMENT] Create dev investment for project ID: {new_investment.project_id}')

    try:
        project = await db.get(DevProject, new_investment.project_id)
        if not project:
            log.warning(f'[INVESTMENT] Dev project ID: {new_investment.project_id} not found')
            return JSONResponse({"status": "fail", "error": f"Project with id {new_investment.project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

        investment = DevInvestment(
            date=new_investment.date,
            project_id=new_investment.project_id,
            amount=new_investment.amount,
            vendor=new_investment.vendor,
            category=new_investment.category if new_investment.category is not None else "cloud",
            description=new_investment.description,
        )
        db.add(investment)
        await db.commit()
        await db.refresh(investment)
        investment_data = investment.to_dict()
        log.info(f'[INVESTMENT] Dev investment created: {investment_data}')
        return JSONResponse({"status": "success", "data": investment_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'[INVESTMENT] Failed to create dev investment: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@dev_tracking_router.put("/investment/{investment_id}")
async def update_investment(investment_id: int, new_investment: UpdateInvestment, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Update dev investment by id
    Args:
        investment_id: Dev investment ID to update
        new_investment: New dev investment information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[INVESTMENT] Update dev investment ID: {investment_id}')

    old_investment = await db.get(DevInvestment, investment_id)
    if not old_investment:
        log.warning(f'[INVESTMENT] Dev investment ID: {investment_id} not found')
        return JSONResponse({"status": "fail", "error": f"Investment with id {investment_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    if new_investment.project_id is not None:
        project = await db.get(DevProject, new_investment.project_id)
        if not project:
            log.warning(f'[INVESTMENT] Dev project ID: {new_investment.project_id} not found')
            return JSONResponse({"status": "fail", "error": f"Project with id {new_investment.project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        for field_name, field_value in new_investment:
            if field_value is not None:
                setattr(old_investment, field_name, field_value)
        await db.commit()
        await db.refresh(old_investment)
        log.info(f'[INVESTMENT] Dev investment updated: {old_investment.to_dict()}')
        return JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'[INVESTMENT] Failed to update dev investment: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@dev_tracking_router.delete("/investment/{investment_id}")
async def delete_investment(investment_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Delete dev investment by id
    Args:
        investment_id: Dev investment ID to delete
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[INVESTMENT] Delete dev investment ID: {investment_id}')

    investment = await db.get(DevInvestment, investment_id)
    if not investment:
        log.warning(f'[INVESTMENT] Dev investment ID: {investment_id} not found')
        return JSONResponse({"status": "fail", "error": f"Investment with id {investment_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(investment)
        await db.commit()
        log.info(f'[INVESTMENT] Dev investment deleted ID: {investment_id}')
        return JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'[INVESTMENT] Failed to delete dev investment: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


# ---------------------------------------------------------------------------
# ProjectDownload
# ---------------------------------------------------------------------------

@dev_tracking_router.get("/download_list")
async def get_download_list(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get all project downloads in the database.
    Args:
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified list of ProjectDownload objects
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info('[DOWNLOAD] Query all project downloads')
    downloads = (await db.scalars(select(ProjectDownload))).all()
    data = []
    for d in downloads:
        data.append(d.to_dict())
    log.info(f"[DOWNLOAD] {str(len(data))} project downloads found")

    return JSONResponse({
        "status": "success",
        "data": data,
    }, status_code=status.HTTP_200_OK, media_type='application/json')


@dev_tracking_router.get("/download/{download_id}")
async def get_download(download_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get project download by id
    Args:
        download_id: The project download to query
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified ProjectDownload object
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[DOWNLOAD] Query project download ID: {download_id}')

    download = await db.get(ProjectDownload, download_id)
    if not download:
        log.warning(f'[DOWNLOAD] Project download ID: {download_id} not found')
        return JSONResponse({"status": "fail", "error": f"Download with id {download_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    download_data = download.to_dict()
    log.info(f'[DOWNLOAD] Query project download: {download_data}')

    return JSONResponse({"status": "success", "data": download_data}, status_code=status.HTTP_200_OK, media_type='application/json')


class CreateDownload(BaseModel):
    project_id: int
    platform: str | None = "github"
    download_count: int | None = 0
    star_count: int | None = None
    date: date_type


class UpdateDownload(BaseModel):
    project_id: int | None = None
    platform: str | None = None
    download_count: int | None = None
    star_count: int | None = None
    date: date_type | None = None


@dev_tracking_router.post("/download")
async def create_download(new_download: CreateDownload, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Create a new project download record
    Args:
        new_download: New project download information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success', 'data': download}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[DOWNLOAD] Create project download for project ID: {new_download.project_id}')

    try:
        project = await db.get(DevProject, new_download.project_id)
        if not project:
            log.warning(f'[DOWNLOAD] Dev project ID: {new_download.project_id} not found')
            return JSONResponse({"status": "fail", "error": f"Project with id {new_download.project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

        download = ProjectDownload(
            project_id=new_download.project_id,
            date=new_download.date,
            platform=new_download.platform if new_download.platform is not None else "github",
            download_count=new_download.download_count if new_download.download_count is not None else 0,
            star_count=new_download.star_count,
        )
        db.add(download)
        await db.commit()
        await db.refresh(download)
        download_data = download.to_dict()
        log.info(f'[DOWNLOAD] Project download created: {download_data}')
        return JSONResponse({"status": "success", "data": download_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'[DOWNLOAD] Failed to create project download: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@dev_tracking_router.put("/download/{download_id}")
async def update_download(download_id: int, new_download: UpdateDownload, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Update project download by id
    Args:
        download_id: Project download ID to update
        new_download: New project download information
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[DOWNLOAD] Update project download ID: {download_id}')

    old_download = await db.get(ProjectDownload, download_id)
    if not old_download:
        log.warning(f'[DOWNLOAD] Project download ID: {download_id} not found')
        return JSONResponse({"status": "fail", "error": f"Download with id {download_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    if new_download.project_id is not None:
        project = await db.get(DevProject, new_download.project_id)
        if not project:
            log.warning(f'[DOWNLOAD] Dev project ID: {new_download.project_id} not found')
            return JSONResponse({"status": "fail", "error": f"Project with id {new_download.project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        for field_name, field_value in new_download:
            if field_value is not None:
                setattr(old_download, field_name, field_value)
        await db.commit()
        await db.refresh(old_download)
        log.info(f'[DOWNLOAD] Project download updated: {old_download.to_dict()}')
        return JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'[DOWNLOAD] Failed to update project download: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


@dev_tracking_router.delete("/download/{download_id}")
async def delete_download(download_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Delete project download by id
    Args:
        download_id: Project download ID to delete
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        return JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'[DOWNLOAD] Delete project download ID: {download_id}')

    download = await db.get(ProjectDownload, download_id)
    if not download:
        log.warning(f'[DOWNLOAD] Project download ID: {download_id} not found')
        return JSONResponse({"status": "fail", "error": f"Download with id {download_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(download)
        await db.commit()
        log.info(f'[DOWNLOAD] Project download deleted ID: {download_id}')
        return JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'[DOWNLOAD] Failed to delete project download: {format_exc()}')
        return JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


# ---------------------------------------------------------------------------
# GithubRepo
# ---------------------------------------------------------------------------

async def _find_tracked_repo(db: AsyncSession, full_name: str, exclude_id: int | None = None) -> GithubRepo | None:
    """
    Find the tracked repo with this name (case-insensitive, GitHub names are), ignoring `exclude_id`
    Args:
        db: Database session
        full_name: Repository "owner/name"
        exclude_id: Repo ID to leave out of the search (the row being updated)

    Returns:
        The matching GithubRepo or None
    """
    stmt = select(GithubRepo).where(func.lower(GithubRepo.full_name) == full_name.lower())
    if exclude_id is not None:
        stmt = stmt.where(GithubRepo.id != exclude_id)
    repo = await db.scalar(stmt)
    return repo


async def _rename_github_repo(db: AsyncSession, repo: GithubRepo, value: str) -> None:
    """
    Apply a new repository name and clear the cached numbers so the row never shows another repo's stats
    Args:
        db: Database session
        repo: Tracked repo being updated
        value: New "owner/name" or github.com URL

    Raises:
        ValueError: Malformed name, or already tracked by another row
    """
    full_name = parse_repo_full_name(value)
    if await _find_tracked_repo(db, full_name, exclude_id=repo.id):
        raise ValueError(f"GitHub repo {full_name} is already tracked")
    if full_name == repo.full_name:
        return
    repo.full_name = full_name
    repo.star_count = None
    repo.download_count = None
    repo.last_synced_at = None
    repo.last_error = None


@dev_tracking_router.get("/github_repo_list")
async def get_github_repo_list(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get all tracked GitHub repos with their latest stars, downloads and sync status.
    Args:
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified list of GithubRepo objects
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        response = JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
        return response
    log.info('[GITHUB_REPO] Query all GitHub repos')
    repos = (await db.scalars(select(GithubRepo).order_by(GithubRepo.id))).all()
    data = []
    for r in repos:
        data.append(r.to_dict())
    log.info(f"[GITHUB_REPO] {str(len(data))} GitHub repos found")

    response = JSONResponse({"status": "success", "data": data}, status_code=status.HTTP_200_OK, media_type='application/json')
    return response


@dev_tracking_router.get("/github_repo/{repo_id}")
async def get_github_repo(repo_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Get a tracked GitHub repo by id
    Args:
        repo_id: The tracked repo to query
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Jsonified GithubRepo object
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        response = JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
        return response
    log.info(f'[GITHUB_REPO] Query GitHub repo ID: {repo_id}')

    repo = await db.get(GithubRepo, repo_id)
    if not repo:
        log.warning(f'[GITHUB_REPO] GitHub repo ID: {repo_id} not found')
        response = JSONResponse({"status": "fail", "error": f"GitHub repo with id {repo_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')
        return response

    repo_data = repo.to_dict()
    log.info(f'[GITHUB_REPO] Query GitHub repo: {repo_data}')

    response = JSONResponse({"status": "success", "data": repo_data}, status_code=status.HTTP_200_OK, media_type='application/json')
    return response


class CreateGithubRepo(BaseModel):
    project_id: int
    full_name: str  # "owner/name" or a github.com URL


class UpdateGithubRepo(BaseModel):
    project_id: int | None = None
    full_name: str | None = None


@dev_tracking_router.post("/github_repo")
async def create_github_repo(new_repo: CreateGithubRepo, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Track a GitHub repo for a dev project and pull its stars and downloads right away; a failed pull keeps the repo tracked with the reason in `last_error` and the next scheduled sync retries it
    Args:
        new_repo: Project ID and repository "owner/name" (or github.com URL)
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success', 'data': repo}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        response = JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
        return response
    log.info(f'[GITHUB_REPO] Track GitHub repo {new_repo.full_name} for project ID: {new_repo.project_id}')

    try:
        full_name = parse_repo_full_name(new_repo.full_name)
        project = await db.get(DevProject, new_repo.project_id)
        if not project:
            log.warning(f'[GITHUB_REPO] Dev project ID: {new_repo.project_id} not found')
            response = JSONResponse({"status": "fail", "error": f"Project with id {new_repo.project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')
            return response
        if await _find_tracked_repo(db, full_name):
            log.warning(f'[GITHUB_REPO] GitHub repo {full_name} is already tracked')
            response = JSONResponse({"status": "fail", "error": f"GitHub repo {full_name} is already tracked"}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
            return response

        repo = GithubRepo(project_id=new_repo.project_id, full_name=full_name)
        db.add(repo)
        await db.commit()
        await db.refresh(repo)
        # The row is committed first so a GitHub outage still leaves the repo tracked; the sync sets counts or `last_error` and writes today's snapshot
        try:
            await sync_github_repos(db, repo.id)
        except Exception:
            # The row is already committed, a rollback only clears a failed transaction so the refresh below can reload it
            await db.rollback()
            log.warning(f'[GITHUB_REPO] Initial sync of {full_name} failed, the scheduled sync will retry: {format_exc()}')
        await db.refresh(repo)
        repo_data = repo.to_dict()
        log.info(f'[GITHUB_REPO] GitHub repo tracked: {repo_data}')
        response = JSONResponse({"status": "success", "data": repo_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
        return response
    except Exception as err:
        log.error(f'[GITHUB_REPO] Failed to track GitHub repo: {format_exc()}')
        response = JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
        return response


@dev_tracking_router.put("/github_repo/{repo_id}")
async def update_github_repo(repo_id: int, new_repo: UpdateGithubRepo, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Update a tracked GitHub repo by id (partial). Renaming clears its cached numbers until the next sync.
    Args:
        repo_id: Tracked repo ID to update
        new_repo: New project ID and/or repository name
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        response = JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
        return response
    log.info(f'[GITHUB_REPO] Update GitHub repo ID: {repo_id}')

    old_repo = await db.get(GithubRepo, repo_id)
    if not old_repo:
        log.warning(f'[GITHUB_REPO] GitHub repo ID: {repo_id} not found')
        response = JSONResponse({"status": "fail", "error": f"GitHub repo with id {repo_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')
        return response

    if new_repo.project_id is not None:
        project = await db.get(DevProject, new_repo.project_id)
        if not project:
            log.warning(f'[GITHUB_REPO] Dev project ID: {new_repo.project_id} not found')
            response = JSONResponse({"status": "fail", "error": f"Project with id {new_repo.project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')
            return response

    try:
        if new_repo.project_id is not None:
            old_repo.project_id = new_repo.project_id
        if new_repo.full_name is not None:
            await _rename_github_repo(db, old_repo, new_repo.full_name)
        await db.commit()
        await db.refresh(old_repo)
        log.info(f'[GITHUB_REPO] GitHub repo updated: {old_repo.to_dict()}')
        response = JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
        return response
    except Exception as err:
        log.error(f'[GITHUB_REPO] Failed to update GitHub repo: {format_exc()}')
        response = JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
        return response


@dev_tracking_router.delete("/github_repo/{repo_id}")
async def delete_github_repo(repo_id: int, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Stop tracking a GitHub repo by id (its past daily snapshots stay in dev_project_downloads)
    Args:
        repo_id: Tracked repo ID to delete
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success'}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        response = JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
        return response
    log.info(f'[GITHUB_REPO] Delete GitHub repo ID: {repo_id}')

    repo = await db.get(GithubRepo, repo_id)
    if not repo:
        log.warning(f'[GITHUB_REPO] GitHub repo ID: {repo_id} not found')
        response = JSONResponse({"status": "fail", "error": f"GitHub repo with id {repo_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')
        return response

    try:
        await db.delete(repo)
        await db.commit()
        log.info(f'[GITHUB_REPO] GitHub repo deleted ID: {repo_id}')
        response = JSONResponse({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
        return response
    except Exception as err:
        log.error(f'[GITHUB_REPO] Failed to delete GitHub repo: {format_exc()}')
        response = JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
        return response


@dev_tracking_router.post("/github_sync/{repo_id}")
@dev_tracking_router.post("/github_sync")
async def github_sync(repo_id: int | None = None, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """
    Manually refresh stars and release downloads from GitHub, for one tracked repo or for all of them.

    Without the path segment `repo_id` is an optional query parameter. Every refreshed project gets
    today's `github` snapshot in dev_project_downloads created or updated in place. A repo whose
    fetch fails is reported in `failed` with its `last_error`; the others still succeed.
    Args:
        repo_id: Tracked repo to refresh, None for all
        current_user: Signed in user
        db: Database session(Created by `get_db`)

    Returns:
        Response body: {'status': 'success', 'data': {'synced': [repo, ...], 'failed': [repo, ...]}}/{'status': 'fail', 'error': error message}
    """
    log = user_log(current_user.id)
    if not await permission_check('dev', current_user.id, db):
        response = JSONResponse({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
        return response
    log.info(f'[GITHUB_SYNC] Manual GitHub sync requested for repo ID: {repo_id if repo_id is not None else "all"}')

    if repo_id is not None and not await db.get(GithubRepo, repo_id):
        log.warning(f'[GITHUB_SYNC] GitHub repo ID: {repo_id} not found')
        response = JSONResponse({"status": "fail", "error": f"GitHub repo with id {repo_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')
        return response

    try:
        result = await sync_github_repos(db, repo_id)
        response = JSONResponse({"status": "success", "data": {"synced": result.synced, "failed": result.failed}}, status_code=status.HTTP_200_OK, media_type='application/json')
        return response
    except Exception as err:
        log.error(f'[GITHUB_SYNC] GitHub sync failed: {format_exc()}')
        response = JSONResponse({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
        return response
