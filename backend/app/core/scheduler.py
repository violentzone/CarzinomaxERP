"""
Background jobs, one AsyncIOScheduler per process (single worker only), started and stopped by the FastAPI lifespan
"""
import asyncio
import json
import smtplib
from datetime import date, timedelta
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
from app.models import auth, hr, finance, dev_tracking, scm

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

async def query_hr_summary(session: AsyncSession) -> dict[str, object]:
    """
    Aggregate the HR figures the summary prompt asks for (users, departments, attendance, leave, paychecks), in SQL
    Args:
        session: Open async session, the caller owns it

    Returns:
        Dict of counts, totals and dates, JSON-ready except for the `date` / `datetime` values
    """
    today = date.today()
    month_start = today.replace(day=1)
    user = auth.User
    user_stmt = select(func.count(user.id), func.count(user.id).filter(user.is_active), func.count(user.id).filter(user.is_active.is_(False)), func.count(user.id).filter(user.has_finance_access, user.has_scm_access, user.has_hr_access, user.has_dev_access), func.count(user.id).filter(user.has_finance_access), func.count(user.id).filter(user.has_scm_access), func.count(user.id).filter(user.has_hr_access), func.count(user.id).filter(user.has_dev_access))
    user_count, active_users, inactive_users, administrators, finance_users, scm_users, hr_users, dev_users = (await session.execute(user_stmt)).one()
    department_stmt = select(func.count(hr.Department.id), func.count(hr.Department.id).filter(hr.Department.manager_id.is_(None)))
    department_count, departments_without_manager = (await session.execute(department_stmt)).one()
    attendance_stmt = select(func.count(hr.AttendanceLog.id).filter(hr.AttendanceLog.date == today), func.count(hr.AttendanceLog.id).filter(hr.AttendanceLog.date == today, hr.AttendanceLog.clock_out.is_(None)), func.coalesce(func.sum(hr.AttendanceLog.total_hours).filter(hr.AttendanceLog.date >= month_start), 0))
    attendance_today, still_clocked_in, working_hours_this_month = (await session.execute(attendance_stmt)).one()
    # Oldest pending request by creation time, users on leave today by the approved date range
    leave_stmt = select(func.count(hr.LeaveRequest.id).filter(hr.LeaveRequest.status == 'pending'), func.min(hr.LeaveRequest.created_at).filter(hr.LeaveRequest.status == 'pending'), func.count(distinct(hr.LeaveRequest.user_id)).filter(hr.LeaveRequest.status == 'approved', hr.LeaveRequest.start_date <= today, hr.LeaveRequest.end_date >= today))
    pending_leave_requests, oldest_pending_leave_created_at, users_on_leave_today = (await session.execute(leave_stmt)).one()
    paycheck_stmt = select(func.count(hr.Paycheck.id).filter(hr.Paycheck.status == 'draft'), func.count(hr.Paycheck.id).filter(hr.Paycheck.status == 'paid'), func.coalesce(func.sum(hr.Paycheck.net_pay).filter(hr.Paycheck.status == 'paid', hr.Paycheck.payment_date >= month_start), 0), func.min(hr.Paycheck.payment_date).filter(hr.Paycheck.status == 'draft', hr.Paycheck.payment_date >= today), func.count(hr.Paycheck.id).filter(hr.Paycheck.status == 'draft', hr.Paycheck.payment_date < today))
    draft_paychecks, paid_paychecks, net_pay_paid_this_month, next_draft_payment_date, overdue_draft_paychecks = (await session.execute(paycheck_stmt)).one()
    summary = {'user_count': user_count, 'active_users': active_users, 'inactive_users': inactive_users, 'administrators': administrators, 'users_per_module': {'finance': finance_users, 'scm': scm_users, 'hr': hr_users, 'dev': dev_users}, 'department_count': department_count, 'departments_without_manager': departments_without_manager, 'attendance_today': attendance_today, 'still_clocked_in': still_clocked_in, 'working_hours_this_month': float(working_hours_this_month), 'pending_leave_requests': pending_leave_requests, 'oldest_pending_leave_created_at': oldest_pending_leave_created_at, 'users_on_leave_today': users_on_leave_today, 'draft_paychecks': draft_paychecks, 'paid_paychecks': paid_paychecks, 'net_pay_paid_this_month': float(net_pay_paid_this_month), 'next_draft_payment_date': next_draft_payment_date, 'overdue_draft_paychecks': overdue_draft_paychecks}
    return summary

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

async def query_finance_summary(session: AsyncSession) -> dict[str, object]:
    """
    Aggregate the Finance figures the summary prompt asks for, in SQL, so the payload stays small as expenses accumulate
    Args:
        session: Open async session, the caller owns it

    Returns:
        Dict of counts, totals and dates over every expense, JSON-ready except for the `date` / `datetime` values
    """
    today = date.today()
    month_start = today.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    expense = finance.Finance  # alias, every statement below reads this table
    expense_stmt = select(func.count(expense.id), func.coalesce(func.sum(expense.amount), 0), func.coalesce(func.sum(expense.amount).filter(expense.expense_date >= month_start), 0), func.coalesce(func.sum(expense.amount).filter(expense.expense_date >= last_month_start, expense.expense_date < month_start), 0), func.coalesce(func.max(expense.amount), 0), func.max(expense.created_at))
    expense_count, expense_total, expense_this_month, expense_last_month, largest_expense, newest_expense_created_at = (await session.execute(expense_stmt)).one()
    type_stmt = select(expense.expense_type, func.sum(expense.amount)).group_by(expense.expense_type)
    expense_per_type = {expense_type.value: float(total) for expense_type, total in (await session.execute(type_stmt)).all()}
    # Unpaid = no paid_date; overdue = unpaid with a due date before today
    unpaid_stmt = select(func.count(expense.id).filter(expense.paid_date.is_(None)), func.coalesce(func.sum(expense.amount).filter(expense.paid_date.is_(None)), 0), func.count(expense.id).filter(expense.paid_date.is_(None), expense.due_date < today), func.coalesce(func.sum(expense.amount).filter(expense.paid_date.is_(None), expense.due_date < today), 0), func.min(expense.due_date).filter(expense.paid_date.is_(None), expense.due_date >= today))
    unpaid_expenses, unpaid_total, overdue_expenses, overdue_total, next_due_date = (await session.execute(unpaid_stmt)).one()
    summary = {'expense_count': expense_count, 'expense_total': float(expense_total), 'expense_this_month': float(expense_this_month), 'expense_last_month': float(expense_last_month), 'expense_per_type': expense_per_type, 'largest_expense': float(largest_expense), 'newest_expense_created_at': newest_expense_created_at, 'unpaid_expenses': unpaid_expenses, 'unpaid_total': float(unpaid_total), 'overdue_expenses': overdue_expenses, 'overdue_total': float(overdue_total), 'next_due_date': next_due_date}
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
            log.info('[SUMMARY] Querying HR')
            hr_summary = await query_hr_summary(session)
            log.info('[SUMMARY] Querying Finance')
            finance_summary = await query_finance_summary(session)
            log.info('[SUMMARY] Querying Dev Tracking')
            dev_summary = await query_dev_tracking_summary(session)
            scm_data_stmt = select(scm.Product)
            scm_data = (await session.execute(scm_data_stmt)).scalars().all()

        # Reformat and send to LLM for summary
        datas = {'hr data': hr_summary, 'finance data': finance_summary, 'dev_tracking data': dev_summary, 'scm data': [d.to_dict() for d in scm_data]}
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
    Scheduled project summary mail, job id `summary_mail`, schedule from the `SUMMARY_SEND_*` settings
    Never raises, APScheduler reports job errors through std `logging` which is not forwarded to loguru
    Returns:
        List of account email sent, empty when nobody opted in or when anything failed
    """
    log.info('[SUMMARY_MAIL] started')
    try:
        # Get users with summary sending
        async with SessionLocal() as session:
            stmt = select(auth.User.email).where(auth.User.send_summary == True)
            mails = list((await session.execute(stmt)).scalars().all())
        # No recipient means no LLM call and no mail, an empty To header would be refused by the SMTP server
        if not mails:
            log.info('[SUMMARY_MAIL] no user opted in, nothing sent')
            return mails
        summary = await generate_summary()
        # smtplib is sync with a 30 s timeout, a thread keeps the event loop free
        sent = await asyncio.to_thread(send_email, mails, 'Carzinomax Dev summary', summary)
    except Exception:
        log.error(f'[SUMMARY_MAIL] failed: {format_exc()}')
        return []
    log.info(f'[SUMMARY_MAIL] finished, sent to {len(sent)} recipient(s)')
    return sent

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
    scheduler.add_job(send_summary, summary_trigger, id='summary_mail', name='Project summary mail', replace_existing=True, misfire_grace_time=3600, coalesce=True)

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
    summary = asyncio.run(generate_summary())
    print(summary)
