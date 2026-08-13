"""
Idempotency Manager — prevents duplicate financial operations.

Uses PostgreSQL as the permanent source of truth for idempotency keys,
making the system immune to cache evictions.
"""

import hashlib
import json
import uuid
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.idempotency.models import IdempotencyKey


class IdempotencyManager:
    """
    Async context manager for idempotent request processing.

    Guarantees at-most-once execution for requests with the same key.
    Uses PostgreSQL for distributed locking and response caching.
    """

    def __init__(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        idempotency_key: str | None,
        payload_dict: dict[str, Any],
    ):
        self.db = db
        self.user_id = str(user_id)
        self.idempotency_key = idempotency_key

        payload_str = json.dumps(payload_dict, sort_keys=True)
        self.payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

        self.is_cached = False
        self.cached_response: JSONResponse | None = None
        self.idem_record: IdempotencyKey | None = None

    async def __aenter__(self):
        if not self.idempotency_key:
            return self

        # 1. Check if this key exists
        stmt = select(IdempotencyKey).where(
            IdempotencyKey.user_id == self.user_id,
            IdempotencyKey.idempotency_key == self.idempotency_key,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Payload mismatch
            if existing.request_hash != self.payload_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key already used for a different payload.",
                )

            # Thundering herd
            if existing.status == "processing":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A request with this idempotency key is currently processing.",
                )

            # Completed
            if existing.status == "completed":
                self.is_cached = True
                self.cached_response = JSONResponse(
                    status_code=existing.response_code or 200,
                    content=existing.response_body,
                )
                return self

        # 2. Acquire lock by inserting a new 'processing' record
        try:
            self.idem_record = IdempotencyKey(
                user_id=self.user_id,
                idempotency_key=self.idempotency_key,
                request_hash=self.payload_hash,
                status="processing",
            )
            self.db.add(self.idem_record)
            await self.db.commit()  # Make it immediately visible to other requests
        except IntegrityError:
            # Another request inserted it at the exact same millisecond
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A request with this idempotency key is currently processing.",
            )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        If an exception occurred during the route execution, we must
        delete the idempotency key so the user can retry.
        """
        if exc_type and self.idem_record:
            # The database session might be in an error state (e.g. if the route 
            # triggered an IntegrityError). We must rollback first.
            await self.db.rollback()
            await self.db.delete(self.idem_record)
            await self.db.commit()

    async def save_response(self, status_code: int, response_data: dict[str, Any]):
        """
        Cache the successful response in the database.
        """
        if not self.idem_record:
            return

        self.idem_record.status = "completed"
        self.idem_record.response_code = status_code
        self.idem_record.response_body = response_data
        
        # Merge is required in case the object became detached
        self.db.add(self.idem_record)
        await self.db.commit()
