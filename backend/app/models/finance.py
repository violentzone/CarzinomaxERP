from datetime import date
from typing import List, Optional
from sqlalchemy import String, Numeric, Date, ForeignKey, Text, Integer, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

class GLAccount(Base, TimestampMixin):
    __tablename__ = "gl_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # asset, liability, equity, revenue, expense
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    journal_lines: Mapped[List["JournalLine"]] = relationship(back_populates="gl_account")

class JournalEntry(Base, TimestampMixin):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # draft, posted

    lines: Mapped[List["JournalLine"]] = relationship(back_populates="journal_entry", cascade="all, delete-orphan")

class JournalLine(Base, TimestampMixin):
    __tablename__ = "journal_lines"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    journal_entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False)
    gl_account_id: Mapped[int] = mapped_column(ForeignKey("gl_accounts.id"), nullable=False)
    debit: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    credit: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)

    journal_entry: Mapped["JournalEntry"] = relationship(back_populates="lines")
    gl_account: Mapped["GLAccount"] = relationship(back_populates="journal_lines")

class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    partner_name: Mapped[str] = mapped_column(String(255), nullable=False)  # Customer or Vendor Name
    invoice_type: Mapped[str] = mapped_column(String(50), nullable=False)  # customer, vendor
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # draft, unpaid, paid, cancelled

    lines: Mapped[List["InvoiceLine"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    # No delete cascade: payments are cash records and survive invoice deletion (invoice_id → NULL)
    payments: Mapped[List["Payment"]] = relationship(back_populates="invoice")

class InvoiceLine(Base, TimestampMixin):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=1.0)
    unit_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.0)  # e.g. 15.00 for 15%
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)

    invoice: Mapped["Invoice"] = relationship(back_populates="lines")

class FixedAsset(Base, TimestampMixin):
    __tablename__ = "fixed_assets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # Buildings, Vehicles, IT Equipment, etc.
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    cost: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    depreciation_method: Mapped[str] = mapped_column(String(50), default="straight_line", nullable=False)  # straight_line, double_declining
    current_value: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # active, depreciated, disposed

class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        # Backstop: a category may only carry its own reference field. Presence is
        # NOT required here (ON DELETE SET NULL must never violate the constraint);
        # required-ness is enforced at the API layer on create.
        CheckConstraint(
            "(invoice_id IS NULL OR category = 'procurement') AND "
            "(employee_id IS NULL OR category = 'salary') AND "
            "(contract_number IS NULL OR category = 'rent')",
            name="ck_payments_category_refs",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # procurement, salary, rent, utilities, tax, subscription, travel, loan_repayment, other
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="procurement", index=True)
    invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)  # procurement only (optional)
    # Cross-module FK kept relationship-free so HR deletes never touch finance ORM state
    employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)  # salary only
    contract_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # rent only
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)  # cash, bank_transfer, credit_card
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # TXN/cheque no., utility account, tax ref, ...

    invoice: Mapped[Optional["Invoice"]] = relationship(back_populates="payments")
