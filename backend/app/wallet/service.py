"""
Wallet service — business logic layer.

Enforces business rules for wallet management:
1. **One wallet per currency per user** — prevents ambiguity in transfers.
2. **Ownership checks** — users can only view/modify their own wallets.
3. **Status transitions** — validates state changes (e.g., can't close
   a wallet with non-zero balance).

This layer sits between routes and repository. It never touches
SQLAlchemy directly — all DB operations go through WalletRepository.
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.wallet.repository import WalletRepository
from app.wallet.schemas import WalletRead


class WalletService:
    """
    Wallet business logic.

    All methods are static. Each takes an AsyncSession and the
    current authenticated user for authorization checks.
    """

    # =====================================================================
    # Create
    # =====================================================================

    @staticmethod
    async def create_wallet(
        db: AsyncSession,
        user: User,
        currency: str,
    ) -> WalletRead:
        """
        Create a new wallet for the authenticated user.

        Business rules:
        1. User cannot have two wallets of the same currency.
           If they already have a USD wallet, creating another → 409.
        2. New wallets start with zero balance and "active" status.

        Why one per currency?
        - Simplifies transfers: "Send 50 USD to user@example.com"
          unambiguously identifies both the sender and receiver wallets.
        - Multiple wallets of the same currency would require users
          to specify WHICH wallet, adding UX complexity with no benefit.
        """
        # Check for duplicate currency
        existing = await WalletRepository.get_wallet_by_user_and_currency(
            db, str(user.id), currency
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You already have a {currency} wallet.",
            )

        # Create the wallet
        wallet = await WalletRepository.create_wallet(
            db=db,
            user_id=str(user.id),
            currency=currency,
        )
        await db.commit()
        await db.refresh(wallet)

        return WalletRead.from_wallet(wallet)

    # =====================================================================
    # Read
    # =====================================================================

    @staticmethod
    async def get_user_wallets(
        db: AsyncSession,
        user: User,
    ) -> list[WalletRead]:
        """
        List all wallets belonging to the authenticated user.

        Returns an empty list if the user has no wallets.
        No authorization check needed — we filter by user.id.
        """
        wallets = await WalletRepository.get_wallets_by_user(
            db, str(user.id)
        )
        return [WalletRead.from_wallet(w) for w in wallets]

    @staticmethod
    async def get_wallet_by_id(
        db: AsyncSession,
        user: User,
        wallet_id: str,
    ) -> WalletRead:
        """
        Fetch a specific wallet by ID.

        Authorization: the wallet must belong to the requesting user.
        Returning 404 (not 403) for wallets belonging to other users
        prevents information leakage — the attacker can't determine
        whether a wallet ID exists or belongs to someone else.
        """
        wallet = await WalletRepository.get_wallet_by_id(db, wallet_id)

        if not wallet or str(wallet.user_id) != str(user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found.",
            )

        return WalletRead.from_wallet(wallet)

    # =====================================================================
    # Update
    # =====================================================================

    @staticmethod
    async def update_wallet_status(
        db: AsyncSession,
        user: User,
        wallet_id: str,
        new_status: str,
    ) -> WalletRead:
        """
        Update a wallet's status (freeze, unfreeze, close).

        Business rules:
        1. Wallet must belong to the requesting user.
        2. Cannot close a wallet with non-zero balance.
           (Funds must be transferred out first.)
        3. Valid transitions:
           - active → frozen (fraud hold, user request)
           - frozen → active (cleared by review)
           - active → closed (only if balance == 0)
           - frozen → closed (only if balance == 0)
        """
        wallet = await WalletRepository.get_wallet_by_id(db, wallet_id)

        if not wallet or str(wallet.user_id) != str(user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found.",
            )

        # Can't close a wallet with balance
        if new_status == "closed" and wallet.balance != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Cannot close a wallet with non-zero balance. "
                    f"Current balance: {wallet.balance / 100:.2f} {wallet.currency}."
                ),
            )

        # Can't reopen a closed wallet
        if wallet.status == "closed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify a closed wallet.",
            )

        await WalletRepository.update_wallet_status(db, wallet_id, new_status)
        await db.commit()

        # Refresh to get updated values
        updated = await WalletRepository.get_wallet_by_id(db, wallet_id)
        return WalletRead.from_wallet(updated)
