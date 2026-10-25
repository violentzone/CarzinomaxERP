"""
Background jobs, one AsyncIOScheduler per process (single worker only), started and stopped by the FastAPI lifespan
"""
import asyncio
import json
import smtplib
from datetime import date
from email.message import EmailMessage
from traceback import format_exc
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage, SystemMessage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.github import sync_github_repos
from app.core.log_module import system_log
from app.core.util_store import load_prompt
from app.ai_service import llm
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

async def query_dev_tracking_summary(session: AsyncSession) -> dict[str, object]:
    """
    Aggregate the Dev Tracking figures the summary prompt asks for, in SQL, so the LLM gets numbers instead of raw rows
    Args:
        session: Open async session, the caller owns it

    Returns:
        Dict of counts, totals and newest dates over every project, JSON-ready except for the `date` / `datetime` values
    """
    # Left join keeps projects without a repo, distinct keeps a project with several repos from counting twice
    project_stmt = select(func.count(distinct(dev_tracking.DevProject.project_id)), func.count(distinct(dev_tracking.DevProject.project_id)).filter(dev_tracking.GithubRepo.id.is_(None))).outerjoin(dev_tracking.GithubRepo, dev_tracking.GithubRepo.project_id == dev_tracking.DevProject.project_id)
    project_count, projects_without_repo = (await session.execute(project_stmt)).one()
    month_start = date.today().replace(day=1)
    investment_stmt = select(func.coalesce(func.sum(dev_tracking.DevInvestment.amount), 0), func.coalesce(func.sum(dev_tracking.DevInvestment.amount).filter(dev_tracking.DevInvestment.date >= month_start), 0))
    investment_total, investment_this_month = (await session.execute(investment_stmt)).one()
    category_stmt = select(dev_tracking.DevInvestment.category, func.sum(dev_tracking.DevInvestment.amount)).group_by(dev_tracking.DevInvestment.category)
    investment_per_category = {category: float(total) for category, total in (await session.execute(category_stmt)).all()}
    repo_stmt = select(func.count(dev_tracking.GithubRepo.id), func.coalesce(func.sum(dev_tracking.GithubRepo.star_count), 0), func.coalesce(func.sum(dev_tracking.GithubRepo.download_count), 0), func.max(dev_tracking.GithubRepo.last_synced_at), func.count(dev_tracking.GithubRepo.id).filter(dev_tracking.GithubRepo.last_error.is_not(None)))
    repo_count, repo_star_total, repo_download_total, last_github_sync, repos_with_sync_error = (await session.execute(repo_stmt)).one()
    snapshot_stmt = select(func.count(dev_tracking.ProjectDownload.id), func.max(dev_tracking.ProjectDownload.date))
    snapshot_count, newest_snapshot_date = (await session.execute(snapshot_stmt)).one()
    summary = {'project_count': project_count, 'projects_without_repo': projects_without_repo, 'investment_total': float(investment_total), 'investment_this_month': float(investment_this_month), 'investment_per_category': investment_per_category, 'repo_count': repo_count, 'repo_star_total': repo_star_total, 'repo_download_total': repo_download_total, 'last_github_sync': last_github_sync, 'repos_with_sync_error': repos_with_sync_error, 'snapshot_count': snapshot_count, 'newest_snapshot_date': newest_snapshot_date}
    return summary

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
            log.info('[SUMMARY] Querying Dev Tracking')
            dev_summary = await query_dev_tracking_summary(session)
            scm_data_stmt = select(scm.Product)
            scm_data = (await session.execute(scm_data_stmt)).scalars().all()

        # Reformat and send to LLM for summary
        datas = {'user data:': [d.to_dict() for d in user_data], 'finance data': [d.to_dict() for d in finance_data], 'dev_tracking data': dev_summary, 'scm data': [d.to_dict() for d in scm_data]}
    except Exception as e:
        log.error(f"[SUMMARY] generate_summary failed: {e}")
        raise ValueError(f"Unable to query data from database")
    # Load prompt
    summary_prompt = load_prompt('project_summary.md')
    messages = [SystemMessage(content=summary_prompt), HumanMessage(content=json.dumps(datas, default=str))]
    try:
        # The shared ChatLiteLLM model, the same one the chat orchestrator uses
        response = await llm.ainvoke(messages)
        summary = response.text
        return summary
    except Exception:
        log.error(f'[SUMMARY] generate_summary failed: {format_exc()}')
        raise ValueError('generate_summary failed')

def send_email(send_to: list[str], subject: str, body: str) -> list[str]:
    """
    Send email from mail address set in .env file, if any of `SMTP_HOSTNAME`, `SMTP_PORT`, `MAIL_FROM` or `SMTP_PASSWORD` env variables are not set, error will raise
    Args:
        send_to: List of email addresses to send to
        subject: Subject of the email
        body: Body of the email

    Returns:
        List of successfully sent emails address
    """
    msg = EmailMessage()
    msg["From"] = settings.MAIL_FROM
    msg['To'] = ', '.join(send_to)
    msg['Subject'] = subject
    msg.set_content(body)
    try:
        # 465 is implicit SSL, anything else (587) connects plain and upgrades with STARTTLS
        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOSTNAME, settings.SMTP_PORT, timeout=30)
        else:
            server = smtplib.SMTP(settings.SMTP_HOSTNAME, settings.SMTP_PORT, timeout=30)
            server.starttls()
        with server:
            server.login(settings.MAIL_FROM, settings.SMTP_PASSWORD)
            refused = server.send_message(msg)
    except Exception:
        log.error(f'[EMAIL] send to {send_to} failed: {format_exc()}')
        raise
    for addr, reason in refused.items():
        log.warning(f'[EMAIL] {addr} refused: {reason}')
    sent = [addr for addr in send_to if addr not in refused]
    log.info(f'[EMAIL] sent "{subject}" to {len(sent)}/{len(send_to)} recipient(s)')
    return sent

async def send_summary() -> list[str]:
    """
    Scheduled function to send summary email
    Returns:
        List of account email sent
    """
    # Get users with summary sending
    async with SessionLocal() as session:
        stmt = select(auth.User.email).where(auth.User.send_summary == True)
        mails = list((await session.execute(stmt)).scalars().all())
    # No recipient means no LLM call and no mail, an empty To header would be refused by the SMTP server
    if not mails:
        log.info('[SUMMARY] no user opted in, nothing sent')
        return mails
    # Call generate summary function
    summary = await generate_summary()
    try:
        # smtplib is sync with a 30 s timeout, a thread keeps the event loop free
        sent = await asyncio.to_thread(send_email, mails, 'Carzinomax Dev summary', summary)
    except Exception:
        log.error(f'[SUMMARY] send_summary failed: {format_exc()}')
        raise ValueError('send_summary failed')
    return sent

async def summary_mail_job() -> None:
    """
    Scheduled project summary mail, job id `summary_mail`, schedule from the `SUMMARY_SEND_*` settings
    Never raises, APScheduler reports job errors through std `logging` which is not forwarded to loguru
    """
    log.info('[SUMMARY_MAIL] started')
    try:
        sent = await send_summary()
    except Exception:
        log.error(f'[SUMMARY_MAIL] failed: {format_exc()}')
        return
    log.info(f'[SUMMARY_MAIL] finished, sent to {len(sent)} recipient(s)')

def start_scheduler() -> None:
    """
    Register the background jobs and start the scheduler, must run inside the event loop (the FastAPI lifespan does)
    Jobs: `github_sync` (GITHUB_SYNC_CRON) and `summary_mail` (SUMMARY_SEND_TIME / SUMMARY_SEND_FREQ / SUMMARY_SEND_WEEKDAY / SUMMARY_SEND_MONTHDAY,
    recipients = users with `send_summary`). Planned, not implemented: the monthly payroll job (PAYCHECK_CALCULATE_TIMESPOT)
    """
    log.info('[SCHEDULER] Function started')
    try:
        trigger = CronTrigger.from_crontab(settings.GITHUB_SYNC_CRON)
        scheduler.add_job(github_sync_job, trigger, id='github_sync', name='GitHub stars/downloads sync', replace_existing=True, misfire_grace_time=3600, coalesce=True)
    except ValueError as err:
        # A bad cron string must not stop the app, the job is skipped
        log.error(f"[SCHEDULER] invalid GITHUB_SYNC_CRON '{settings.GITHUB_SYNC_CRON}' ({err}), github_sync not registered")

    # SUMMARY_* values are range-checked by config.py at startup, SUMMARY_SEND_TIME is the hour in server local time
    if settings.SUMMARY_SEND_FREQ == 'day':
        summary_trigger = CronTrigger(hour=settings.SUMMARY_SEND_TIME, minute=0)
    elif settings.SUMMARY_SEND_FREQ == 'week':
        summary_trigger = CronTrigger(day_of_week=settings.SUMMARY_SEND_WEEKDAY, hour=settings.SUMMARY_SEND_TIME, minute=0)
    else:
        summary_trigger = CronTrigger(day=settings.SUMMARY_SEND_MONTHDAY, hour=settings.SUMMARY_SEND_TIME, minute=0)
    scheduler.add_job(summary_mail_job, summary_trigger, id='summary_mail', name='Project summary mail', replace_existing=True, misfire_grace_time=3600, coalesce=True)

    scheduler.start()
    log.info(f'[SCHEDULER]  Initialized and started ({len(scheduler.get_jobs())} job(s)).')
    for job in scheduler.get_jobs():
        log.info(f"[SCHEDULER]  job '{job.id}' next run at {job.next_run_time}")


def shutdown_scheduler() -> None:
    """
    Shutdown the scheduler
    """
    scheduler.shutdown()
    log.info('[SCHEDULER] Scheduler: Stopped.')

if __name__ == '__main__':
    asyncio.run(generate_summary())
