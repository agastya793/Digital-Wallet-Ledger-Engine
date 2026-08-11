"""
Idempotency Manager — prevents duplicate financial operations.

Problem:
    Network retries are common. If a client sends a transfer request,
    the network drops before receiving the response, and the client
    retries, the user gets charged twice. In fintech, this is catastrophic.

Solution:
    The client sends an `Idempotency-Key` header with each mutation request.
    The server uses this key to:
    1. Lock the request (SETNX in Redis) to prevent thundering herd.
    2. Execute the operation and cache the response.
    3. On retry: return the cached response instead of re-executing.

How it works:
    1. Client sends:  POST /transfers/p2p  Idempotency-Key: abc-123
    2. First request:  lock key → execute transfer → cache result → return 200.
    3. Retry request:  find cached result → return same 200 (no double-charge).
    4. Same key, different payload: → 409 Conflict (key reuse protection).

Implementation:
    Async context manager pattern — clean, explicit, no middleware magic.

    async with IdempotencyManager(redis, user_id, key, payload) as idem:
        if idem.is_cached:
            return idem.cached_response
        result = await do_work()
        await idem.save_response(200, result)
        return result

Redis key structure:
    "idem:{user_id}:{idempotency_key}" → JSON { status, request_hash, response }

TTL:
    Processing lock: 60 seconds (auto-release if app crashes).
    Completed response: 24 hours (configurable via settings).
"""

import hashlib
import json
import uuid
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
import redis.asyncio as aioredis

from app.config import settings


class IdempotencyManager:
    """
    Async context manager for idempotent request processing.

    Guarantees at-most-once execution for requests with the same key.
    Uses Redis for distributed locking and response caching.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        user_id: uuid.UUID,
        idempotency_key: str | None,
        payload_dict: dict[str, Any],
    ):
        self.redis = redis_client
        self.user_id = user_id
        self.idempotency_key = idempotency_key

        # Hash the payload to detect key reuse with different data.
        # sort_keys=True ensures {"a":1,"b":2} and {"b":2,"a":1}
        # produce the same hash.
        payload_str = json.dumps(payload_dict, sort_keys=True)
        self.payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

        # Redis key: scoped to user + idempotency key.
        # This means different users can use the same key string
        # without collision.
        self.redis_key: str | None = None
        if self.idempotency_key:
            self.redis_key = f"idem:{self.user_id}:{self.idempotency_key}"

        self.is_cached = False
        self.cached_response: JSONResponse | None = None

    async def __aenter__(self):
        """
        Enter the idempotency context.

        Three possible outcomes:
        1. No idempotency key provided → pass through (no-op).
        2. Key exists with completed response → set is_cached=True.
        3. Key doesn't exist → acquire processing lock.
        """
        # No key = bypass idempotency entirely.
        if not self.redis_key:
            return self

        # Check if this key has been used before.
        existing_raw = await self.redis.get(self.redis_key)

        if existing_raw:
            existing = json.loads(existing_raw)

            # Payload mismatch: same key, different request body.
            # This catches bugs where a client accidentally reuses
            # an idempotency key for a different operation.
            if existing.get("request_hash") != self.payload_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key already used for a different payload.",
                )

            # Currently being processed by another request.
            # (Thundering herd: two identical requests hit at the same time.)
            if existing.get("status") == "processing":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A request with this idempotency key is currently processing.",
                )

            # Completed: return the cached response.
            if existing.get("status") == "completed":
                self.is_cached = True
                self.cached_response = JSONResponse(
                    status_code=existing.get("status_code", 200),
                    content=existing.get("response_data"),
                )
                return self

        # Acquire processing lock with SETNX (set-if-not-exists).
        processing_state = json.dumps({
            "status": "processing",
            "request_hash": self.payload_hash,
        })

        # NX=True: only set if key doesn't exist (atomic lock).
        # EX=60: auto-expire in 60s if app crashes during processing.
        #        This prevents permanent lock-out.
        lock_acquired = await self.redis.set(
            self.redis_key,
            processing_state,
            nx=True,
            ex=60,
        )

        if not lock_acquired:
            # Another request acquired the lock in the last millisecond.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A request with this idempotency key is currently processing.",
            )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the idempotency context.

        If an unhandled exception occurred, release the lock so the
        client can retry with the same key. We don't cache errors —
        only successful responses should be idempotent.
        """
        if exc_type and self.redis_key:
            await self.redis.delete(self.redis_key)

    async def save_response(self, status_code: int, response_data: dict):
        """
        Cache the successful response in Redis.

        After this call, any future request with the same idempotency
        key will receive this cached response instead of re-executing.

        TTL is configured via IDEMPOTENCY_KEY_TTL_HOURS (default 24h).
        After the TTL expires, the key can be reused for a fresh operation.
        """
        if not self.redis_key:
            return

        ttl_seconds = settings.IDEMPOTENCY_KEY_TTL_HOURS * 3600

        final_state = json.dumps({
            "status": "completed",
            "request_hash": self.payload_hash,
            "status_code": status_code,
            "response_data": response_data,
        })

        await self.redis.set(self.redis_key, final_state, ex=ttl_seconds)
