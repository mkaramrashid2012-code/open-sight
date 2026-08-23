"""Database module for async session support."""
from app.core.db import db_manager, Base

# Create async session factory for async operations
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, async_scoped_session
from asyncio import current_task
from app.core.config import settings
from sqlalchemy import text

# Use the async_database_url property from settings
ASYNC_DATABASE_URL = settings.async_database_url

# Create async engine
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.debug,
)

# Create async session factory
AsyncSessionLocal = async_scoped_session(
    async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    ),
    scopefunc=current_task,
)

async def init_async_db():
    """Initialize async database connection."""
    async with async_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
        await conn.commit()

async def close_async_db():
    """Close async database connections."""
    await async_engine.dispose()
