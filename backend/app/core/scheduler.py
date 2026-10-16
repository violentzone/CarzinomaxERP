"""
Background jobs, one AsyncIOScheduler per process (single worker only), started and stopped by the FastAPI lifespan
"""
from traceback import format_exc

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.github import sync_github_repos
from app.core.log_module import system_log

scheduler = AsyncIOScheduler()

system_log = system_log()


async def github_sync_job() -> None:
    """
    Scheduled GitHub stars/downloads sync, job id `github_sync`, cron from `GITHUB_SYNC_CRON`
    Opens its own session and never raises, APScheduler reports job errors through std `logging` which is not forwarded to loguru
    """
    system_log.info('Scheduler: github_sync started')
    try:
        async with SessionLocal() as session:
            result = await sync_github_repos(session)
    except Exception:
        system_log.error(f'Scheduler: github_sync failed: {format_exc()}')
        return
    for row in result.failed:
        system_log.warning(f"Scheduler: github_sync {row['full_name']} (repo {row['id']}) failed: {row['last_error']}")
    system_log.info(f'Scheduler: github_sync finished, {len(result.synced)} synced, {len(result.failed)} failed')


def start_scheduler() -> None:
    """
    Register the background jobs and start the scheduler, must run inside the event loop (the FastAPI lifespan does)
    Jobs: `github_sync` (GITHUB_SYNC_CRON). The monthly payroll job (PAYCHECK_CALCULATE_TIMESPOT) is planned, not implemented.
    """
    try:
        trigger = CronTrigger.from_crontab(settings.GITHUB_SYNC_CRON)
        scheduler.add_job(github_sync_job, trigger, id='github_sync', name='GitHub stars/downloads sync', replace_existing=True, misfire_grace_time=3600, coalesce=True)
        system_log.info(f"Scheduler: github_sync registered (cron '{settings.GITHUB_SYNC_CRON}')")
    except ValueError as err:
        # A bad cron string must not stop the app, the job is skipped
        system_log.error(f"Scheduler: invalid GITHUB_SYNC_CRON '{settings.GITHUB_SYNC_CRON}' ({err}), github_sync not registered")

    scheduler.start()
    system_log.info(f'Scheduler: Initialized and started ({len(scheduler.get_jobs())} job(s)).')
    for job in scheduler.get_jobs():
        system_log.info(f"Scheduler: job '{job.id}' next run at {job.next_run_time}")


def shutdown_scheduler() -> None:
    """
    Shutdown the scheduler
    """
    scheduler.shutdown()
    system_log.info('Scheduler: Stopped.')
