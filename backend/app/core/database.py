from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Create database engine
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False,  # Set to True for SQL logging
    future=True,
)

# Create session maker
SessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Sync engine: same database, psycopg (v3) driver instead of asyncpg
SYNC_DATABASE_URL = settings.ASYNC_DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg://", 1
)

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    future=True,
)

# Sync session maker
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Dependency to get db session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator to retrieve an asynchronous database session.

    Yields:
        AsyncSession: An active SQLAlchemy AsyncSession.

    Raises:
        Exception: Rolls back the transaction if any exception occurs.
    """
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Generator[Session, None, None]:
    """Dependency generator to retrieve a synchronous database session.

    Yields:
        Session: An active SQLAlchemy Session.

    Raises:
        Exception: Rolls back the transaction if any exception occurs.
    """
    with SyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
