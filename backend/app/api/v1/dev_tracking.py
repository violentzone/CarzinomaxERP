"""
Dev tracking module, Query, add, remove and update DevProject, DevInvestment and ProjectDownload
"""
from datetime import date as date_type
from decimal import Decimal
from traceback import format_exc

from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse as Response
from pydantic import BaseModel
from sqlalchemy import select
from starlette import status

from app.api.common import get_current_user, permission_check
from app.core.database import get_db
from app.core.log_module import user_log
from app.models import DevInvestment, DevProject, ProjectDownload, User

dev_tracking_router = APIRouter(prefix="/dev_tracking", tags=["Dev Tracking"])


# ---------------------------------------------------------------------------
# DevProject
# ---------------------------------------------------------------------------

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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info('Query all dev projects')
    projects = (await db.scalars(select(DevProject))).all()
    data = []
    for p in projects:
        data.append(p.to_dict())
    log.info(f"{str(len(data))} dev projects found")

    return Response({
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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Query dev project ID: {project_id}')

    project = await db.get(DevProject, project_id)
    if not project:
        log.warning(f'Dev project ID: {project_id} not found')
        return Response({"status": "fail", "error": f"Project with id {project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    project_data = project.to_dict()
    log.info(f'Query dev project: {project_data}')

    return Response({"status": "success", "data": project_data}, status_code=status.HTTP_200_OK, media_type='application/json')


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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Create dev project with name: {new_project.project_name}')

    try:
        project = DevProject(
            project_name=new_project.project_name,
            project_description=new_project.project_description,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        project_data = project.to_dict()
        log.info(f'Dev project created: {project_data}')
        return Response({"status": "success", "data": project_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to create dev project: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Update dev project ID: {project_id}')

    old_project = await db.get(DevProject, project_id)
    if not old_project:
        log.warning(f'Dev project ID: {project_id} not found')
        return Response({"status": "fail", "error": f"Project with id {project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        for field_name, field_value in new_project:
            if field_value is not None:
                setattr(old_project, field_name, field_value)
        await db.commit()
        await db.refresh(old_project)
        log.info(f'Dev project updated: {old_project.to_dict()}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to update dev project: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Delete dev project ID: {project_id}')

    project = await db.get(DevProject, project_id)
    if not project:
        log.warning(f'Dev project ID: {project_id} not found')
        return Response({"status": "fail", "error": f"Project with id {project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(project)
        await db.commit()
        log.info(f'Dev project deleted ID: {project_id}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to delete dev project: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info('Query all dev investments')
    investments = (await db.scalars(select(DevInvestment))).all()
    data = []
    for i in investments:
        data.append(i.to_dict())
    log.info(f"{str(len(data))} dev investments found")

    return Response({
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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Query dev investment ID: {investment_id}')

    investment = await db.get(DevInvestment, investment_id)
    if not investment:
        log.warning(f'Dev investment ID: {investment_id} not found')
        return Response({"status": "fail", "error": f"Investment with id {investment_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    investment_data = investment.to_dict()
    log.info(f'Query dev investment: {investment_data}')

    return Response({"status": "success", "data": investment_data}, status_code=status.HTTP_200_OK, media_type='application/json')


class CreateInvestment(BaseModel):
    project_id: int
    amount: Decimal
    vendor: str
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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Create dev investment for project ID: {new_investment.project_id}')

    try:
        project = await db.get(DevProject, new_investment.project_id)
        if not project:
            log.warning(f'Dev project ID: {new_investment.project_id} not found')
            return Response({"status": "fail", "error": f"Project with id {new_investment.project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

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
        log.info(f'Dev investment created: {investment_data}')
        return Response({"status": "success", "data": investment_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to create dev investment: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Update dev investment ID: {investment_id}')

    old_investment = await db.get(DevInvestment, investment_id)
    if not old_investment:
        log.warning(f'Dev investment ID: {investment_id} not found')
        return Response({"status": "fail", "error": f"Investment with id {investment_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    if new_investment.project_id is not None:
        project = await db.get(DevProject, new_investment.project_id)
        if not project:
            log.warning(f'Dev project ID: {new_investment.project_id} not found')
            return Response({"status": "fail", "error": f"Project with id {new_investment.project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        for field_name, field_value in new_investment:
            if field_value is not None:
                setattr(old_investment, field_name, field_value)
        await db.commit()
        await db.refresh(old_investment)
        log.info(f'Dev investment updated: {old_investment.to_dict()}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to update dev investment: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Delete dev investment ID: {investment_id}')

    investment = await db.get(DevInvestment, investment_id)
    if not investment:
        log.warning(f'Dev investment ID: {investment_id} not found')
        return Response({"status": "fail", "error": f"Investment with id {investment_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(investment)
        await db.commit()
        log.info(f'Dev investment deleted ID: {investment_id}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to delete dev investment: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info('Query all project downloads')
    downloads = (await db.scalars(select(ProjectDownload))).all()
    data = []
    for d in downloads:
        data.append(d.to_dict())
    log.info(f"{str(len(data))} project downloads found")

    return Response({
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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Query project download ID: {download_id}')

    download = await db.get(ProjectDownload, download_id)
    if not download:
        log.warning(f'Project download ID: {download_id} not found')
        return Response({"status": "fail", "error": f"Download with id {download_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    download_data = download.to_dict()
    log.info(f'Query project download: {download_data}')

    return Response({"status": "success", "data": download_data}, status_code=status.HTTP_200_OK, media_type='application/json')


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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Create project download for project ID: {new_download.project_id}')

    try:
        project = await db.get(DevProject, new_download.project_id)
        if not project:
            log.warning(f'Dev project ID: {new_download.project_id} not found')
            return Response({"status": "fail", "error": f"Project with id {new_download.project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

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
        log.info(f'Project download created: {download_data}')
        return Response({"status": "success", "data": download_data}, status_code=status.HTTP_201_CREATED, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to create project download: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Update project download ID: {download_id}')

    old_download = await db.get(ProjectDownload, download_id)
    if not old_download:
        log.warning(f'Project download ID: {download_id} not found')
        return Response({"status": "fail", "error": f"Download with id {download_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    if new_download.project_id is not None:
        project = await db.get(DevProject, new_download.project_id)
        if not project:
            log.warning(f'Dev project ID: {new_download.project_id} not found')
            return Response({"status": "fail", "error": f"Project with id {new_download.project_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        for field_name, field_value in new_download:
            if field_value is not None:
                setattr(old_download, field_name, field_value)
        await db.commit()
        await db.refresh(old_download)
        log.info(f'Project download updated: {old_download.to_dict()}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to update project download: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')


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
        return Response({"status": "fail", "error": "Permission denied"}, status_code=status.HTTP_403_FORBIDDEN, media_type='application/json')
    log.info(f'Delete project download ID: {download_id}')

    download = await db.get(ProjectDownload, download_id)
    if not download:
        log.warning(f'Project download ID: {download_id} not found')
        return Response({"status": "fail", "error": f"Download with id {download_id} not found"}, status_code=status.HTTP_404_NOT_FOUND, media_type='application/json')

    try:
        await db.delete(download)
        await db.commit()
        log.info(f'Project download deleted ID: {download_id}')
        return Response({"status": "success"}, status_code=status.HTTP_200_OK, media_type='application/json')
    except Exception as err:
        log.error(f'Failed to delete project download: {format_exc()}')
        return Response({"status": "fail", 'error': str(err)}, status_code=status.HTTP_400_BAD_REQUEST, media_type='application/json')
