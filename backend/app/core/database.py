from collections.abc import AsyncGenerator

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

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

# Declarative base class for models
class Base(DeclarativeBase):

    def to_dict(self) -> dict[str, object]:
        """Return mapped column values as a dict (relationships excluded)."""
        return {
            attr.key: getattr(self, attr.key)
            for attr in inspect(self).mapper.column_attrs
        }

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
