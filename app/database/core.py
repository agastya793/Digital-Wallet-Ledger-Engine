"""
Async SQLAlchemy engine and session factory.

This module creates:
1. An async engine connected to PostgreSQL via asyncpg.
2. An async session factory for creating database sessions.

Usage:
    from app.database.core import async_engine, AsyncSessionLocal
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# ---- Async Engine ----
# create_async_engine wraps asyncpg with SQLAlchemy's connection pool.
# Key settings pulled from config:
#   pool_size:       number of persistent connections
#   max_overflow:    extra connections allowed during traffic spikes
#   pool_timeout:    seconds to wait for a connection before error
#   echo:            log all SQL queries (True in dev, False in prod)
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    # pool_pre_ping: test connections before using them.
    # Prevents "server closed the connection unexpectedly" errors
    # after idle periods (common with Neon serverless).
)

# ---- Session Factory ----
# async_sessionmaker creates AsyncSession instances.
# expire_on_commit=False: prevents implicit lazy-loading after commit.
# In async code, lazy-loading triggers synchronous I/O → DetachedInstanceError.
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
