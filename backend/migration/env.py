"""Alembic environment.

Resolves the database URL from the app's settings (same .env as the server)
and registers every model on Base.metadata for autogenerate support.

Two online modes:
- CLI (`alembic upgrade head`, `alembic revision --autogenerate ...`): builds
  its own async engine and runs migrations through it.
- Programmatic (app startup in main.py): the app passes its already-open
  connection via config.attributes["connection"]; migrations join that
  connection/transaction and the app owns the commit.
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import inspect, pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.core.config import settings
from app.models.base import Base
import app.models  # noqa: F401 — imports every model module so all tables register on Base.metadata

config = context.config

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emits SQL to stdout, no DB needed."""
    context.configure(
        url=settings.ASYNC_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def _ensure_baseline(connection) -> None:
    """Bring pre-Alembic databases under version control.

    Databases created by the old create_all flow have the full schema but no
    alembic_version table; running the 0001 baseline against them would fail
    with "relation already exists". Stamp them at 0001 instead so upgrades
    start from the later revisions. Fresh (empty) databases are left alone —
    0001 builds them. The app startup path in main.py does the same check.
    """
    inspector = inspect(connection)
    if inspector.has_table("alembic_version") or not inspector.has_table("users"):
        return
    connection.execute(text(
        "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, "
        "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
    ))
    connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0001')"))


async def run_async_migrations() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = settings.ASYNC_DATABASE_URL
    connectable = async_engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    # Own transaction, committed before migrations run — alembic manages the
    # migration transaction itself on the second connection.
    async with connectable.begin() as connection:
        await connection.run_sync(_ensure_baseline)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection", None)
    if connection is not None:
        # Programmatic path (app startup): reuse the app's connection; skip
        # fileConfig so the app's logging (loguru/uvicorn) is not reconfigured.
        do_run_migrations(connection)
    else:
        if config.config_file_name is not None:
            fileConfig(config.config_file_name, disable_existing_loggers=False)
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
