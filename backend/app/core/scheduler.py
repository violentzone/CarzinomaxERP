from datetime import date
from sqlalchemy.future import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import SessionLocal
from app.core.log_module import system_log
from app.models.hr import Employee
from app.models.finance import Payment

scheduler = AsyncIOScheduler()

async def process_monthly_salary_payments():
    """Calculate total salary for all active employees and create a single payment in the finance module."""
    log = system_log()
    log.info("Scheduler: Starting monthly salary payment execution...")

    async with SessionLocal() as session:
        try:
            # 1. Fetch active employees
            result = await session.execute(
                select(Employee).filter(Employee.status == "active")
            )
            employees = result.scalars().all()

            if not employees:
                log.info("Scheduler: No active employees found. No salary payment processed.")
                return

            today = date.today()
            payment_ref = f"Monthly Salary - {today.strftime('%B %Y')}"

            # 2. Check for duplicate payment for this month (employee_id is None, category is salary, date is today)
            dup_check = await session.execute(
                select(Payment).filter(
                    Payment.employee_id.is_(None),
                    Payment.category == "salary",
                    Payment.payment_date == today
                )
            )
            if dup_check.scalar_one_or_none():
                log.warning(f"Scheduler: Monthly salary payment already exists for {today}. Skipping.")
                return

            # 3. Sum up all active employee salaries
            total_salary = sum(emp.salary for emp in employees)

            if total_salary <= 0:
                log.info("Scheduler: Total active employee salary is 0. No payment processed.")
                return

            # 4. Create the single payment record
            payment = Payment(
                category="salary",
                employee_id=None,
                payment_date=today,
                amount=total_salary,
                payment_method="bank_transfer",
                reference=payment_ref
            )
            session.add(payment)
            await session.commit()
            log.info(f"Scheduler: Successfully processed monthly salary payment of {total_salary} for all active employees.")

        except Exception as e:
            await session.rollback()
            log.error(f"Scheduler: Error processing monthly salary payments: {e}")

def start_scheduler():
    """Initialize and start the scheduler."""
    log = system_log()
    # Schedule the job for the 1st of every month at midnight
    scheduler.add_job(
        process_monthly_salary_payments,
        trigger=CronTrigger(day=1, hour=0, minute=0),
        id="monthly_salary_payments",
        replace_existing=True
    )
    scheduler.start()
    log.info("Scheduler: Initialized and started (cron: 1st of month at midnight).")

def shutdown_scheduler():
    """Shutdown the scheduler."""
    log = system_log()
    scheduler.shutdown()
    log.info("Scheduler: Stopped.")
