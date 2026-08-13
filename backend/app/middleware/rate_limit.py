"""
Rate limiting dependency.

Uses Redis to implement a Fixed Window rate limiter.
Identifies clients by:
1. API Key (if X-API-Key header is present)
2. User ID (if Authorization header with JWT is present)
3. IP Address (fallback for unauthenticated endpoints)
"""

import hashlib

import jwt
from fastapi import HTTPException, Request, status

from app.cache.core import redis_client


class RateLimiter:
    """
    FastAPI dependency for rate limiting endpoints.

    Usage:
        @router.get("/my-endpoint", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
    """

    def __init__(self, times: int, seconds: int):
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request):
        # 1. Endpoint path
        endpoint = request.url.path

        # 2. Extract Identifier
        identifier = self._get_identifier(request)

        # 3. Redis Key
        key = f"rate_limit:{identifier}:{endpoint}"

        # 4. Increment and set expiry
        # Using a pipeline to execute INCR and EXPIRE atomically
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.ttl(key)
            results = await pipe.execute()

        current_count = results[0]
        ttl = results[1]

        # If it's the first request in this window (or key didn't exist/had no TTL), set expiry
        if current_count == 1 or ttl == -1:
            await redis_client.expire(key, self.seconds)

        if current_count > self.times:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )

    def _get_identifier(self, request: Request) -> str:
        # Check API Key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            # Hash it to avoid storing raw API keys in Redis
            return f"apikey:{hashlib.sha256(api_key.encode()).hexdigest()}"

        # Check JWT for User ID
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # We do NOT verify the signature here, just decode to extract 'sub'.
                # The actual auth dependency handles proper verification.
                payload = jwt.decode(token, options={"verify_signature": False})
                if "sub" in payload:
                    return f"user:{payload['sub']}"
            except Exception:
                pass  # If token is invalid, fallback to IP

        # Fallback to IP address
        # Check for X-Forwarded-For if behind a proxy, otherwise use client.host
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Can be a comma-separated list, take the first one (original client)
            ip = forwarded_for.split(",")[0].strip()
            return f"ip:{ip}"

        return f"ip:{request.client.host if request.client else 'unknown'}"
