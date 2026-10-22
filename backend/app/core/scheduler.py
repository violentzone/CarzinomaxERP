"""
Background jobs, one AsyncIOScheduler per process (single worker only), started and stopped by the FastAPI lifespan
"""
from traceback import format_exc
from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import outerjoin

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.github import sync_github_repos
from app.core.log_module import system_log
from app.core.util_store import load_prompt
from app.ai_service.llm_router import LlmRouter
from app.models import auth, finance, dev_tracking, scm

scheduler = AsyncIOScheduler()

log = system_log()


async def github_sync_job() -> None:
    """
    Scheduled GitHub stars/downloads sync, job id `github_sync`, cron from `GITHUB_SYNC_CRON`
    Opens its own session and never raises, APScheduler reports job errors through std `logging` which is not forwarded to loguru
    """
    log.info('[GITHUB_SYNC] started')
    try:
        async with SessionLocal() as session:
            result = await sync_github_repos(session)
    except Exception:
        log.error(f'[GITHUB_SYNC] failed: {format_exc()}')
        return
    for row in result.failed:
        log.warning(f"[GITHUB_SYNC] {row['full_name']} (repo {row['id']}) failed: {row['last_error']}")
    log.info(f'[GITHUB_SYNC] finished, {len(result.synced)} synced, {len(result.failed)} failed')

async def generate_summary() -> str:
    """
    Generate the summary of the data status of Carzinomax Dev
    Returns:
        Markdown formatted string summary
    """
    # Acquire data from DB
    try:
        async with (SessionLocal() as session):
            log.info('[SUMMARY] Querying User')
            user_data_stmt = select(auth.User)
            user_data = (await session.execute(user_data_stmt)).scalars().all()
            log.info('[SUMMARY] Querying Finance')
            finance_data_stmt = select(finance.Finance)
            finance_data = (await session.execute(finance_data_stmt)).scalars().all()
            dev_data_stmt = select(dev_tracking.DevProject, dev_tracking.DevInvestment, dev_tracking.ProjectDownload
                                            ).outerjoin(dev_tracking.DevInvestment, dev_tracking.DevProject.project_id == dev_tracking.DevInvestment.project_id
                                            ).outerjoin(dev_tracking.ProjectDownload, dev_tracking.DevProject.project_id == dev_tracking.DevInvestment.project_id)
            dev_data = (await session.execute(dev_data_stmt)).scalars().all()
            scm_data_stmt = select(scm.Product)
            scm_data = (await session.execute(scm_data_stmt)).scalars().all()

        # Reformat and send to LLM for summary

    except Exception as e:
        log.error(f"[SUMMARY] generate_summary failed: {e}")

    # Load prompt
    summary_prompt = load_prompt('project_summary.md')
    messages = [{'role': 'user', 'content': 'Generate summary'}]
    try:
        llm = LlmRouter()
        summary = await llm.chat(summary_prompt, messages)
        return summary
    except ValueError as err:
        log.error(f"[SUMMARY] generate_summary failed: {err}")
        raise ValueError(f"generate_summary failed")

def start_scheduler() -> None:
    """
    Register the background jobs and start the scheduler, must run inside the event loop (the FastAPI lifespan does)
    Jobs: `github_sync` (GITHUB_SYNC_CRON). The monthly payroll job (PAYCHECK_CALCULATE_TIMESPOT) is planned, not implemented.
    """
    log.info('[SCHEDULER] Function started')
    try:
        trigger = CronTrigger.from_crontab(settings.GITHUB_SYNC_CRON)
        scheduler.add_job(github_sync_job, trigger, id='github_sync', name='GitHub stars/downloads sync', replace_existing=True, misfire_grace_time=3600, coalesce=True)
    except ValueError as err:
        # A bad cron string must not stop the app, the job is skipped
        log.error(f"[SCHEDULER] invalid GITHUB_SYNC_CRON '{settings.GITHUB_SYNC_CRON}' ({err}), github_sync not registered")

    scheduler.start()
    log.info(f'[SCHEDULER]  Initialized and started ({len(scheduler.get_jobs())} job(s)).')
    for job in scheduler.get_jobs():
        log.info(f"[SCHEDULER]  job '{job.id}' next run at {job.next_run_time}")


def shutdown_scheduler() -> None:
    """
    Shutdown the scheduler
    """
    scheduler.shutdown()
    log.info('Scheduler: Stopped.')
