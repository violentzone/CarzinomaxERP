import enum
from sqlalchemy import String, Boolean, Uuid, Enum
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID, uuid4

from app.core.database import Base
from app.models import TimestampMixin


class ExpenseType(str, enum.Enum):
    PAYCHECK = "paycheck"
    PETTY_CASH = "petty_cash"
    INVESTMENT = "investment"
    OTHER = "other"

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
