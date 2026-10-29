import enum
from datetime import date
from typing import Literal, Optional
from sqlalchemy import String, Uuid, Enum, Numeric, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID, uuid4

from app.models.base import Base
from app.models import TimestampMixin


class ExpenseType(str, enum.Enum):
    PAYCHECK = "paycheck"
    PETTY_CASH = "petty_cash"
    INVESTMENT = "investment"
    OTHER = "other"


class ExpenseStatus(str, enum.Enum):
    PAID = "paid"
    UNPAID = "unpaid"
    OVERDUE = "overdue"


# What the money went on; an `investment` with a `project_id` is what Dev Tracking shows as project spend
ExpenseCategory = Literal['cloud', 'software_licenses', 'hardware', 'consulting', 'travel', 'office', 'meals', 'other']


class Finance(Base, TimestampMixin):
    __tablename__ = "finance"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4, index=True)
    expense_type: Mapped[ExpenseType] = mapped_column(
        Enum(
            ExpenseType,
            native_enum=False,
            length=32,
            values_callable=lambda e: [m.value for m in e],
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    vendor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # who was paid
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # invoice / receipt number
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # one of ExpenseCategory
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)  # document date, today when recorded by hand
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    paid_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)  # NULL = unpaid
    planned_pay_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)  # day the accountant intends to pay, NULL = not scheduled
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dev_projects.project_id", ondelete="SET NULL"), nullable=True)
    receipt_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # stored upload, "<user_id>/<uuid>.<ext>" under UPLOAD_DIR
    status: Mapped[ExpenseStatus] = mapped_column(
        Enum(
            ExpenseStatus,
            native_enum=False,
            length=32,
            values_callable=lambda e: [m.value for m in e],
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
    )
