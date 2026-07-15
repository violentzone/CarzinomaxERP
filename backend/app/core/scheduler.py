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
    """Calculate salaries for all active employees and create payments in the finance module."""
    log = system_log()
    log.info("Scheduler: Starting monthly salary payment execution...")

    async with SessionLocal() as session:
        try:
            # 1. Fetch active employees
            result = await session.execute(
                select(Employee).filter(Employee.status == "active")
            )
            employees = result.scalars().all()

            today = date.today()
            payment_ref = f"Monthly Salary - {today.strftime('%B %Y')}"
            payments_created = 0

            for emp in employees:
                # 2. Check for duplicate payments for this employee on this date
                dup_check = await session.execute(
                    select(Payment).filter(
                        Payment.employee_id == emp.id,
                        Payment.category == "salary",
                        Payment.payment_date == today
                    )
                )
                if dup_check.scalar_one_or_none():
                    log.warning(f"Scheduler: Salary payment already exists for employee ID {emp.id} on {today}. Skipping.")
                    continue

                # 3. Create the payment record
                payment = Payment(
                    category="salary",
                    employee_id=emp.id,
                    payment_date=today,
                    amount=emp.salary,
                    payment_method="bank_transfer",
                    reference=payment_ref
                )
                session.add(payment)
                payments_created += 1

            if payments_created > 0:
                await session.commit()
                log.info(f"Scheduler: Successfully processed {payments_created} salary payments.")
            else:
                log.info("Scheduler: No new salary payments processed.")

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
