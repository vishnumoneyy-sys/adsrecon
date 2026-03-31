"""Database setup with async SQLAlchemy 2.0"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency that yields an async session."""
    async with async_session_maker() as session:
        yield session


# Convenience async context manager for use with 'async with'
class async_session:
    """Async context manager that yields an AsyncSession.

    Usage:
        async with async_session() as db:
            result = await db.execute(query)
    """

    def __init__(self):
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> AsyncSession:
        self._session = async_session_maker()
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()


# Re-export for convenience imports
from contextlib import asynccontextmanager


@asynccontextmanager
async def get_async_session():
    """Alternative async context manager for database sessions.

    This version handles commit/rollback automatically.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
