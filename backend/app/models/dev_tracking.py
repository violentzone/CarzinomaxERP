from datetime import date
from typing import Optional
from sqlalchemy import String, Numeric, Date, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin

class DevInvestment(Base, TimestampMixin):
    __tablename__ = "dev_investments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    vendor: Mapped[str] = mapped_column(String(255), nullable=False)  # AWS, GCP, Vercel, etc.
    category: Mapped[str] = mapped_column(String(100), default="cloud", nullable=False)  # cloud, software_licenses, hardware, consulting
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ProjectDownload(Base, TimestampMixin):
    __tablename__ = "dev_project_downloads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), default="github", nullable=False)  # github, dockerhub, npm
    download_count: Mapped[int] = mapped_column(nullable=False, default=0)
    star_count: Mapped[Optional[int]] = mapped_column(nullable=True)
