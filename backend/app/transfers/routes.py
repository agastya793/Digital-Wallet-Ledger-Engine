"""
Transfer API routes — /api/v1/transfers/*.

Endpoints:
    POST /p2p  — Execute a peer-to-peer money transfer.

All endpoints require authentication (Bearer token).
The sender is always the authenticated user.

Idempotency:
    The /p2p endpoint accepts an optional `Idempotency-Key` header.
    If provided, the request is guaranteed to execute at most once.
    Retries with the same key return the cached response.
    Same key + different payload → 409 Conflict.
"""

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.database.dependencies import get_db
from app.idempotency.service import IdempotencyManager
from app.transfers.schemas import TransferRequest, TransferResponse
from app.transfers.service import TransferService

router = APIRouter()


@router.post(
    "/p2p",
    response_model=TransferResponse,
    summary="Send money to another user",
    responses={
        400: {"description": "Self-transfer, inactive wallet, or insufficient funds"},
        404: {"description": "Recipient not found or sender has no wallet"},
        409: {"description": "Idempotency key conflict"},
    },
)
async def p2p_transfer(
    body: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(
        None,
        alias="Idempotency-Key",
        description=(
            "Optional. Prevents duplicate transfers on network retries. "
            "Must be a unique string per request (e.g., UUID). "
            "Valid for 24 hours."
        ),
    ),
):
    """
    Transfer money from your wallet to another user's wallet.

    - **recipient_email**: The recipient's email address.
    - **amount**: Amount in minor units (e.g., 5000 = $50.00). Must be > 0.
    - **currency**: ISO 4217 currency code (e.g., USD).
    - **description**: Optional transfer note.
    - **Idempotency-Key** (header): Optional. Guarantees at-most-once execution.

    If the recipient doesn't have a wallet in the specified currency,
    one is automatically created for them.

    The transfer is executed atomically — either both wallets are
    updated or neither is.
    """
    # Build payload dict for idempotency hash comparison.
    payload_dict = body.model_dump()

    async with IdempotencyManager(
        db=db,
        user_id=current_user.id,
        idempotency_key=idempotency_key,
        payload_dict=payload_dict,
    ) as idem:

        # If we have a cached response, return it immediately.
        # No work is done — this is a replay of the original response.
        if idem.is_cached:
            return idem.cached_response

        # Execute the transfer (first time).
        result = await TransferService.execute_p2p_transfer(
            db=db,
            sender=current_user,
            recipient_email=body.recipient_email,
            amount=body.amount,
            currency=body.currency,
            description=body.description,
        )

        # Serialize for caching and response.
        response_data = result.model_dump(mode="json")

        # Cache the successful response in Redis.
        await idem.save_response(200, response_data)

        return JSONResponse(status_code=200, content=response_data)
