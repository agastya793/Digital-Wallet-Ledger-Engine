"""
Redis cache client — connection setup and FastAPI dependency.

Provides:
1. A shared Redis client (async, connection-pooled).
2. A FastAPI dependency (`get_redis`) for injecting into routes.

Used by:
- Idempotency system (Phase 10): storing processed request keys.
- Rate limiting (future): tracking request counts per user.
- Caching (future): hot data like user profiles, wallet balances.
"""

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.config import settings

# =============================================================================
# Redis Client
# =============================================================================
# Single client at module level. redis.asyncio manages a connection pool
# internally — each `await client.get()` borrows a connection and returns
# it when done. Safe for concurrent async code.
# =============================================================================
redis_client = aioredis.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_POOL_SIZE,
    encoding="utf-8",
    decode_responses=True,
    # decode_responses=True: Redis returns bytes by default.
    # With this flag, values are automatically decoded to str.
)


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """
    FastAPI dependency that yields the shared Redis client.

    The client is shared across requests (not per-request).
    The dependency pattern keeps it testable — tests can override.
    """
    yield redis_client
