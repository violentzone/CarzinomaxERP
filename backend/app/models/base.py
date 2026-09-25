from datetime import datetime, timezone

from fastapi.encoders import jsonable_encoder
from sqlalchemy import DateTime, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Declarative base class for models
class Base(DeclarativeBase):

    def to_dict(self) -> dict[str, object]:
        """Return mapped column values as a JSON-safe dict (relationships excluded).

        Values are passed through ``jsonable_encoder`` so datetimes, dates and
        Decimals come back as JSON primitives and the result can be handed
        straight to ``JSONResponse``.
        """
        return jsonable_encoder({
            attr.key: getattr(self, attr.key)
            for attr in inspect(self).mapper.column_attrs
        })


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
