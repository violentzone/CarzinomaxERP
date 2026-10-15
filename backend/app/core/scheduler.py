from traceback import format_exc

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.github import sync_github_repos
from app.core.log_module import system_log

scheduler = AsyncIOScheduler()


async def github_sync_job() -> None:
    """Scheduled GitHub stars/downloads sync (job id ``github_sync``).

    Opens its own session and never raises: APScheduler reports job errors through the
    std ``logging`` module, which this app does not forward to loguru.
    """
    log = system_log()
    log.info("Scheduler: github_sync started")
    try:
        async with SessionLocal() as session:
            result = await sync_github_repos(session)
    except Exception:
        log.error(f"Scheduler: github_sync failed: {format_exc()}")
        return
    for row in result.failed:
        log.warning(f"Scheduler: github_sync {row['full_name']} (repo {row['id']}) failed: {row['last_error']}")
    log.info(f"Scheduler: github_sync finished, {len(result.synced)} synced, {len(result.failed)} failed")


def _register_github_sync() -> None:
    """Register ``github_sync`` from GITHUB_SYNC_CRON; an invalid cron is logged and skipped."""
    log = system_log()
    try:
        trigger = CronTrigger.from_crontab(settings.GITHUB_SYNC_CRON)
    except ValueError as err:
        log.error(f"Scheduler: invalid GITHUB_SYNC_CRON '{settings.GITHUB_SYNC_CRON}' ({err}); "
                  f"github_sync not registered")
        return
    scheduler.add_job(github_sync_job, trigger, id="github_sync", name="GitHub stars/downloads sync",
                      replace_existing=True, misfire_grace_time=3600, coalesce=True)
    log.info(f"Scheduler: github_sync registered (cron '{settings.GITHUB_SYNC_CRON}')")


def start_scheduler() -> None:
    """Register the background jobs and start the scheduler.

    Must run inside the event loop (the FastAPI lifespan does this). Jobs: ``github_sync``
    (GITHUB_SYNC_CRON). The monthly payroll job is still planned, not implemented.
    """
    log = system_log()
    _register_github_sync()
    scheduler.start()
    log.info(f"Scheduler: Initialized and started ({len(scheduler.get_jobs())} job(s)).")
    for job in scheduler.get_jobs():
        log.info(f"Scheduler: job '{job.id}' next run at {job.next_run_time}")


def shutdown_scheduler() -> None:
    """Shutdown the scheduler."""
    log = system_log()
    scheduler.shutdown()
    log.info("Scheduler: Stopped.")
