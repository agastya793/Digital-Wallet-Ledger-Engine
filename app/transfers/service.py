"""
Transfer service — orchestrates P2P money transfers.

This service is an ORCHESTRATOR, not a data layer. It:
1. Validates business rules (self-transfer, active accounts, etc.).
2. Looks up/creates wallets as needed.
3. Constructs the debit/credit operation list.
4. Delegates the actual balance changes to LedgerService.

It NEVER touches wallet balances directly. The LedgerRepository
owns all balance mutations — this service just tells it what to do.

Flow for a P2P transfer (Alice sends $50 to Bob):
    1. Look up Bob by email → 404 if not found.
    2. Verify Alice ≠ Bob → 400 if self-transfer.
    3. Find Alice's USD wallet → 404 if none.
    4. Find Bob's USD wallet → auto-create if missing.
    5. Construct operations: [debit Alice $50, credit Bob $50].
    6. Call LedgerService.execute_transaction().
    7. Return TransferResponse.
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.repository import AuthRepository
from app.ledger.schemas import LedgerOperation
from app.ledger.service import LedgerService
from app.transfers.schemas import TransferResponse
from app.wallet.repository import WalletRepository


class TransferService:
    """
    Money transfer orchestration.

    All methods are static. Each takes an AsyncSession and the
    authenticated user (sender).
    """

    @staticmethod
    async def execute_p2p_transfer(
        db: AsyncSession,
        sender: User,
        recipient_email: str,
        amount: int,
        currency: str,
        description: str | None = None,
    ) -> TransferResponse:
        """
        Execute a peer-to-peer transfer.

        Args:
            db: Async database session.
            sender: The authenticated user sending money.
            recipient_email: Email of the person receiving money.
            amount: Amount in minor units (e.g., 5000 = $50.00).
            currency: ISO 4217 currency code.
            description: Optional transfer note.

        Returns:
            TransferResponse with transaction details.

        Raises:
            HTTPException 400: Self-transfer attempted.
            HTTPException 400: Sender account deactivated.
            HTTPException 404: Recipient not found.
            HTTPException 404: Sender has no wallet in this currency.
            HTTPException 400: Insufficient funds (raised by ledger).
        """

        # =================================================================
        # Step 1: Look up recipient by email
        # =================================================================
        recipient = await AuthRepository.get_user_by_email(db, recipient_email)
        if not recipient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No user found with email {recipient_email}.",
            )

        # =================================================================
        # Step 2: Prevent self-transfers
        # =================================================================
        # A user transferring money to themselves is either a bug or
        # an abuse attempt. Either way, it's not a valid operation.
        if str(sender.id) == str(recipient.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot transfer money to yourself.",
            )

        # =================================================================
        # Step 3: Verify both accounts are active
        # =================================================================
        if not sender.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your account is deactivated.",
            )

        if not recipient.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recipient's account is deactivated.",
            )

        # =================================================================
        # Step 4: Find sender's wallet (must exist)
        # =================================================================
        sender_wallet = await WalletRepository.get_wallet_by_user_and_currency(
            db, str(sender.id), currency
        )
        if not sender_wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"You don't have a {currency} wallet.",
            )

        if sender_wallet.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Your {currency} wallet is {sender_wallet.status}.",
            )

        # =================================================================
        # Step 5: Find or create recipient's wallet
        # =================================================================
        # Auto-creation: if Bob doesn't have a USD wallet, we create one
        # with zero balance to accept the incoming transfer.
        # This matches Venmo/PayPal UX — you can receive money without
        # having explicitly set up a wallet first.
        recipient_wallet = await WalletRepository.get_wallet_by_user_and_currency(
            db, str(recipient.id), currency
        )
        if not recipient_wallet:
            recipient_wallet = await WalletRepository.create_wallet(
                db=db,
                user_id=str(recipient.id),
                currency=currency,
            )
            await db.flush()

        if recipient_wallet.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recipient's {currency} wallet is {recipient_wallet.status}.",
            )

        # =================================================================
        # Step 6: Construct double-entry operations
        # =================================================================
        # This is the core of double-entry bookkeeping:
        # Every transfer has exactly two legs:
        #   1. DEBIT  the sender's wallet  (money out)
        #   2. CREDIT the recipient's wallet (money in)
        # The ledger engine verifies ∑ debits == ∑ credits.
        operations = [
            LedgerOperation(
                wallet_id=sender_wallet.id,
                entry_type="debit",
                amount=amount,
            ),
            LedgerOperation(
                wallet_id=recipient_wallet.id,
                entry_type="credit",
                amount=amount,
            ),
        ]

        # =================================================================
        # Step 7: Delegate to the ledger engine
        # =================================================================
        # The LedgerService handles:
        # - Zero-sum verification (already guaranteed by our 2-leg setup)
        # - Pessimistic locking (SELECT FOR UPDATE)
        # - Insufficient funds check
        # - Atomic balance updates
        # - Ledger entry creation
        # - Commit
        txn = await LedgerService.execute_transaction(
            db=db,
            transaction_type="p2p_transfer",
            operations=operations,
            description=(
                description
                or f"Transfer from {sender.email} to {recipient_email}"
            ),
        )

        # =================================================================
        # Step 8: Return formatted response
        # =================================================================
        return TransferResponse(
            transaction_id=txn.id,
            sender_email=sender.email,
            recipient_email=recipient_email,
            amount=amount,
            amount_display=f"{amount / 100:.2f}",
            currency=currency,
            description=description,
            status=txn.status,
        )
