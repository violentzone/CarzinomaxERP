from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.future import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.log_module import system_log
from app.models.hr import Employee, LeaveRequest, Paycheck
from app.models.finance import Payment

scheduler = AsyncIOScheduler()

async def process_monthly_salary_payments():
    """Calculate total salary for all active employees (less unpaid leave deductions) and create individual paychecks plus a single payment in the finance module."""
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

            # Compute the pay period (previous month)
            # Since scheduler runs on the 1st of the month, the period is the entire previous month
            first_of_this_month = today.replace(day=1)
            pay_period_end = first_of_this_month - timedelta(days=1)
            pay_period_start = pay_period_end.replace(day=1)
            days_in_period = (pay_period_end - pay_period_start).days + 1

            total_net_pay = 0.0

            # 3. Process each employee: calculate unpaid leaves, create Paycheck
            for emp in employees:
                # Query approved unpaid and sick leave requests overlapping with the pay period
                leave_result = await session.execute(
                    select(LeaveRequest).filter(
                        LeaveRequest.employee_id == emp.id,
                        LeaveRequest.status == "approved",
                        LeaveRequest.leave_type.in_(["unpaid", "sick"]),
                        LeaveRequest.start_date <= pay_period_end,
                        LeaveRequest.end_date >= pay_period_start
                    )
                )
                leaves = leave_result.scalars().all()

                # Calculate overlapping leave days by type
                unpaid_days = 0
                sick_days = 0
                for leave in leaves:
                    overlap_start = max(leave.start_date, pay_period_start)
                    overlap_end = min(leave.end_date, pay_period_end)
                    if overlap_start <= overlap_end:
                        days = (overlap_end - overlap_start).days + 1
                        if leave.leave_type == "unpaid":
                            unpaid_days += days
                        elif leave.leave_type == "sick":
                            sick_days += days

                # Calculate deduction: (salary / days_in_period) * (unpaid_days + 0.5 * sick_days)
                salary_dec = Decimal(str(emp.salary))
                daily_rate = salary_dec / Decimal(days_in_period)
                deduction_days = Decimal(unpaid_days) + Decimal("0.5") * Decimal(sick_days)
                deduction = (daily_rate * deduction_days).quantize(Decimal("0.01"))
                net_pay = max(Decimal("0.0"), salary_dec - deduction)

                # Create Paycheck record
                paycheck = Paycheck(
                    employee_id=emp.id,
                    pay_period_start=pay_period_start,
                    pay_period_end=pay_period_end,
                    base_salary=float(salary_dec),
                    allowances=0.0,
                    deductions=float(deduction),
                    net_pay=float(net_pay),
                    payment_date=today,
                    status="paid"
                )
                session.add(paycheck)
                total_net_pay += float(net_pay)

            if total_net_pay <= 0:
                log.info("Scheduler: Total active employee net pay is 0. No payment processed.")
                return

            # 4. Create the single payment record in the finance module
            payment = Payment(
                category="salary",
                employee_id=None,
                payment_date=today,
                amount=total_net_pay,
                payment_method="bank_transfer",
                reference=payment_ref
            )
            session.add(payment)
            await session.commit()
            log.info(f"Scheduler: Successfully generated paychecks and processed monthly salary payment of {total_net_pay} for active employees.")

        except Exception as e:
            await session.rollback()
            log.error(f"Scheduler: Error processing monthly salary payments: {e}")


def start_scheduler():
    """Initialize and start the scheduler."""
    log = system_log()
    # Schedule the job using the configured timespot
    scheduler.add_job(
        process_monthly_salary_payments,
        trigger=CronTrigger.from_crontab(settings.PAYCHECK_CALCULATE_TIMESPOT),
        id="monthly_salary_payments",
        replace_existing=True
    )
    scheduler.start()
    log.info(f"Scheduler: Initialized and started (cron: {settings.PAYCHECK_CALCULATE_TIMESPOT}).")

def shutdown_scheduler():
    """Shutdown the scheduler."""
    log = system_log()
    scheduler.shutdown()
    log.info("Scheduler: Stopped.")
