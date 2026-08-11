"""
FastAPI dependency for database sessions.

Usage in routes:
    @router.get("/items")
    async def list_items(db: AsyncSession = Depends(get_db)):
        ...
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.core import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session, then close it.

    This is a FastAPI dependency — it:
    1. Creates a new session for each request.
    2. Yields it to the route handler.
    3. Automatically closes it when the request finishes.

    The session is NOT auto-committed. Routes must explicitly call
    `await db.commit()` after mutations. This prevents accidental
    partial commits on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
