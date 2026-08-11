"""
Merchant API routes — /api/v1/merchant/*.

Dual authentication system:
- POST /register         → JWT auth (user becomes a merchant)
- POST /checkout         → API key auth (merchant creates payment request)
- GET  /checkout/{id}    → API key auth (merchant checks session status)
- POST /checkout/{id}/pay → JWT auth (customer pays a session)

This demonstrates two auth strategies in one application:
- User-facing endpoints: Authorization: Bearer <JWT>
- Machine-to-machine endpoints: X-API-Key: sk_live_...
"""

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.database.dependencies import get_db
from app.merchant.dependencies import get_current_merchant
from app.merchant.models import MerchantAccount
from app.merchant.schemas import (
    CheckoutCreate,
    CheckoutPayRequest,
    CheckoutRead,
    MerchantRead,
    MerchantRegister,
    MerchantRegisterResponse,
)
from app.merchant.service import MerchantService
from app.merchant.webhooks import send_payment_webhook

router = APIRouter()


# =========================================================================
# User-Authenticated Endpoints (JWT)
# =========================================================================


@router.post(
    "/register",
    response_model=MerchantRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register as a merchant",
    responses={
        409: {"description": "Already registered as a merchant"},
    },
)
async def register_merchant(
    body: MerchantRegister,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register the authenticated user as a merchant.

    Returns an API key that must be saved immediately —
    it is never shown again.

    - **business_name**: Name of your business.
    - **webhook_url**: Optional URL to receive payment notifications.
    """
    return await MerchantService.register_merchant(
        db=db,
        user=current_user,
        business_name=body.business_name,
        webhook_url=body.webhook_url,
    )


@router.post(
    "/checkout/{session_id}/pay",
    response_model=CheckoutRead,
    summary="Pay a checkout session",
    responses={
        400: {"description": "Session not pending, insufficient funds, or inactive wallet"},
        404: {"description": "Session not found or no wallet in required currency"},
    },
)
async def pay_checkout(
    session_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Pay a merchant's checkout session.

    The authenticated user pays the specified amount from their wallet
    to the merchant's wallet. Funds are transferred atomically via
    the ledger engine.

    If the merchant has a webhook URL configured, a payment notification
    is sent asynchronously in the background.
    """
    checkout, merchant = await MerchantService.pay_checkout_session(
        db=db,
        user=current_user,
        session_id=session_id,
    )

    # Fire webhook in background (doesn't block the response).
    if merchant.webhook_url:
        background_tasks.add_task(
            send_payment_webhook,
            webhook_url=merchant.webhook_url,
            session_id=str(checkout.id),
            amount=checkout.amount,
            currency=checkout.currency,
            paid_by_user_id=str(checkout.paid_by_user_id),
            paid_at=checkout.paid_at.isoformat() if checkout.paid_at else "",
            transaction_id=checkout.transaction_id or "",
        )

    return checkout


# =========================================================================
# API-Key-Authenticated Endpoints (X-API-Key)
# =========================================================================


@router.post(
    "/checkout",
    response_model=CheckoutRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a checkout session",
)
async def create_checkout(
    body: CheckoutCreate,
    merchant: MerchantAccount = Depends(get_current_merchant),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a checkout session (payment request).

    Requires API key authentication via X-API-Key header.

    - **amount**: Amount in minor units (e.g., 5000 = $50.00).
    - **currency**: ISO 4217 currency code.
    - **description**: What the customer is paying for.

    Share the returned session ID with your customer for payment.
    """
    return await MerchantService.create_checkout_session(
        db=db,
        merchant=merchant,
        amount=body.amount,
        currency=body.currency,
        description=body.description,
    )


@router.get(
    "/checkout/{session_id}",
    response_model=CheckoutRead,
    summary="Get checkout session status",
)
async def get_checkout(
    session_id: str,
    merchant: MerchantAccount = Depends(get_current_merchant),
    db: AsyncSession = Depends(get_db),
):
    """
    Check the status of a checkout session.

    Requires API key authentication. Only returns sessions
    belonging to the authenticated merchant.
    """
    from sqlalchemy import select
    from app.merchant.models import CheckoutSession

    stmt = select(CheckoutSession).where(
        CheckoutSession.id == session_id,
        CheckoutSession.merchant_id == str(merchant.id),
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkout session not found.",
        )

    return CheckoutRead.from_session(session)
