"""
Merchant service — business logic for merchant operations.

Three core operations:
1. register_merchant:      upgrade a user to merchant, issue API key.
2. create_checkout_session: merchant creates a payment request.
3. pay_checkout_session:    customer fulfills a payment request.

This service orchestrates across multiple domains:
- Auth (user lookup)
- Wallet (find/create wallets)
- Ledger (execute payment transaction)
- Webhooks (notify merchant of payment)
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.ledger.schemas import LedgerOperation
from app.ledger.service import LedgerService
from app.merchant.models import CheckoutSession, MerchantAccount
from app.merchant.schemas import CheckoutRead, MerchantRegisterResponse
from app.merchant.security import generate_api_key, hash_api_key
from app.wallet.repository import WalletRepository


class MerchantService:
    """
    Merchant business logic.

    All methods are static. Each takes an AsyncSession.
    """

    # =====================================================================
    # Registration
    # =====================================================================

    @staticmethod
    async def register_merchant(
        db: AsyncSession,
        user: User,
        business_name: str,
        webhook_url: str | None = None,
    ) -> MerchantRegisterResponse:
        """
        Register a user as a merchant.

        Flow:
        1. Check if user is already a merchant → 409.
        2. Generate a secure API key (sk_live_...).
        3. Hash the API key (SHA-256).
        4. Create MerchantAccount with the hash.
        5. Return the raw API key (one-time only).

        CRITICAL: The raw API key is returned in this response and
        NEVER stored. If the merchant loses it, they must regenerate.
        """
        # Check for existing merchant account
        stmt = select(MerchantAccount).where(
            MerchantAccount.user_id == str(user.id)
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You are already registered as a merchant.",
            )

        # Generate and hash the API key
        raw_api_key = generate_api_key()
        hashed_key = hash_api_key(raw_api_key)

        # Create the merchant account
        merchant = MerchantAccount(
            user_id=str(user.id),
            business_name=business_name,
            hashed_api_key=hashed_key,
            webhook_url=webhook_url,
        )
        db.add(merchant)
        await db.commit()
        await db.refresh(merchant)

        return MerchantRegisterResponse(
            merchant_id=merchant.id,
            business_name=merchant.business_name,
            api_key=raw_api_key,
        )

    # =====================================================================
    # Checkout Sessions
    # =====================================================================

    @staticmethod
    async def create_checkout_session(
        db: AsyncSession,
        merchant: MerchantAccount,
        amount: int,
        currency: str,
        description: str | None = None,
    ) -> CheckoutRead:
        """
        Create a checkout session (payment request).

        Called by the merchant's server via API key auth.
        The session ID is given to the customer to pay.
        """
        session = CheckoutSession(
            merchant_id=str(merchant.id),
            amount=amount,
            currency=currency,
            description=description,
            status="pending",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        return CheckoutRead.from_session(session)

    @staticmethod
    async def pay_checkout_session(
        db: AsyncSession,
        user: User,
        session_id: str,
    ) -> tuple[CheckoutRead, MerchantAccount]:
        """
        Pay a checkout session — customer fulfills a merchant's payment request.

        Flow:
        1. Look up the checkout session → 404 if not found.
        2. Verify session is "pending" → 400 if already paid/cancelled.
        3. Find the merchant's wallet (auto-create if needed).
        4. Find the customer's wallet → 404 if none.
        5. Construct debit (customer) + credit (merchant) operations.
        6. Execute via LedgerService (atomic).
        7. Update session status to "paid".
        8. Return the updated session + merchant (for webhook).

        Returns a tuple of (CheckoutRead, MerchantAccount) so the
        route handler can fire the webhook with merchant details.
        """
        # 1. Look up session with pessimistic lock
        stmt = (
            select(CheckoutSession)
            .where(CheckoutSession.id == session_id)
            .with_for_update()
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Checkout session not found.",
            )

        # 2. Verify status
        if session.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Checkout session is already {session.status}.",
            )

        # 3. Find merchant's user_id via their merchant account
        merchant_stmt = select(MerchantAccount).where(
            MerchantAccount.id == session.merchant_id
        )
        merchant_result = await db.execute(merchant_stmt)
        merchant = merchant_result.scalar_one_or_none()

        if not merchant or not merchant.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Merchant account is not active.",
            )

        # Find or create merchant's wallet for this currency
        merchant_wallet = await WalletRepository.get_wallet_by_user_and_currency(
            db, merchant.user_id, session.currency
        )
        if not merchant_wallet:
            merchant_wallet = await WalletRepository.create_wallet(
                db=db,
                user_id=merchant.user_id,
                currency=session.currency,
            )
            await db.flush()

        # 4. Find customer's wallet
        customer_wallet = await WalletRepository.get_wallet_by_user_and_currency(
            db, str(user.id), session.currency
        )
        if not customer_wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"You don't have a {session.currency} wallet.",
            )

        if customer_wallet.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Your {session.currency} wallet is {customer_wallet.status}.",
            )

        # 5. Construct double-entry operations
        operations = [
            LedgerOperation(
                wallet_id=customer_wallet.id,
                entry_type="debit",
                amount=session.amount,
            ),
            LedgerOperation(
                wallet_id=merchant_wallet.id,
                entry_type="credit",
                amount=session.amount,
            ),
        ]

        # 6. Execute via ledger (atomic)
        txn = await LedgerService.execute_transaction(
            db=db,
            transaction_type="checkout_payment",
            operations=operations,
            description=session.description or f"Payment to {merchant.business_name}",
        )

        # 7. Update session status
        session.status = "paid"
        session.paid_by_user_id = str(user.id)
        session.paid_at = datetime.now(timezone.utc)
        session.transaction_id = str(txn.id)
        await db.commit()
        await db.refresh(session)

        # 8. Return session + merchant for webhook
        return CheckoutRead.from_session(session), merchant
