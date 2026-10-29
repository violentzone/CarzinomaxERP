from datetime import date, datetime
from typing import Optional
from sqlalchemy import BigInteger, String, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.base import TimestampMixin


class DevProject(Base, TimestampMixin):
    __tablename__ = "dev_projects"

    project_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ProjectDownload(Base, TimestampMixin):
    __tablename__ = "dev_project_downloads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("dev_projects.project_id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), default="github", nullable=False)  # github, dockerhub, npm
    download_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)  # release totals exceed int32
    star_count: Mapped[Optional[int]] = mapped_column(nullable=True)


class GithubRepo(Base, TimestampMixin):
    """A GitHub repository tracked for a dev project: latest numbers plus sync status.

    History is not kept here. Every sync also upserts one ProjectDownload row per
    project per UTC day (platform "github") holding the project-wide totals.
    """

    __tablename__ = "dev_github_repos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("dev_projects.project_id", ondelete="CASCADE"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)  # "owner/name"
    star_count: Mapped[Optional[int]] = mapped_column(nullable=True)  # latest stargazers_count
    download_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # sum of release-asset download_count
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # last successful sync
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
