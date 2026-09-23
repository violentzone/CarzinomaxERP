from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.log_module import system_log

scheduler = AsyncIOScheduler()


def start_scheduler():
    """Initialize and start the background scheduler.

    The monthly salary job was removed together with the Employee table;
    register new jobs here with scheduler.add_job() as they are introduced.
    """
    log = system_log()
    scheduler.start()
    log.info("Scheduler: Initialized and started (no jobs registered).")


def shutdown_scheduler():
    """Shutdown the scheduler."""
    log = system_log()
    scheduler.shutdown()
    log.info("Scheduler: Stopped.")
