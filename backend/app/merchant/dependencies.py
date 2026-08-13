"""
Merchant authentication dependency — API key validation.

This is the second authentication system in the app:
- Users authenticate with JWT (Authorization: Bearer <token>)
- Merchants authenticate with API key (X-API-Key: sk_live_...)

The X-API-Key header is hashed and looked up in the database.
If found and active, the merchant account is returned.

Usage:
    @router.post("/checkout")
    async def create_checkout(
        merchant: MerchantAccount = Depends(get_current_merchant),
    ):
        ...
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db
from app.merchant.models import MerchantAccount
from app.merchant.security import hash_api_key

# ---- API Key Scheme ----
# Tells FastAPI (and Swagger UI) to look for X-API-Key header.
# auto_error=False: don't raise 403 automatically if header is missing;
# we want to return a custom 401 message.
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


async def get_current_merchant(
    api_key: str | None = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> MerchantAccount:
    """
    Validate the X-API-Key header and return the merchant account.

    Flow:
    1. Extract X-API-Key from header → 401 if missing.
    2. Hash the key with SHA-256.
    3. Look up the hash in merchant_accounts → 401 if not found.
    4. Check merchant is active → 403 if deactivated.
    5. Return the MerchantAccount instance.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required.",
        )

    # Hash the incoming key and look it up.
    hashed = hash_api_key(api_key)

    stmt = select(MerchantAccount).where(
        MerchantAccount.hashed_api_key == hashed
    )
    result = await db.execute(stmt)
    merchant = result.scalar_one_or_none()

    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    if not merchant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Merchant account is deactivated.",
        )

    return merchant
