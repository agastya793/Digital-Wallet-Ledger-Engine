"""
Wallet repository — data access layer.

Handles all database I/O for the wallets table.
Balance updates are intentionally ABSENT from this repository.
They will be handled in the ledger repository (Phase 8) because
balance changes must be atomic with ledger entry creation.

This module provides:
- CRUD operations for wallet records
- Query by user, by ID, by user+currency
- Status updates (freeze/unfreeze)
"""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.wallet.models import Wallet


class WalletRepository:
    """
    Data access methods for the wallets table.

    All methods are static and accept an AsyncSession.
    No session lifecycle management — that's the caller's job.
    """

    # =====================================================================
    # Create
    # =====================================================================

    @staticmethod
    async def create_wallet(
        db: AsyncSession,
        user_id: str,
        currency: str,
    ) -> Wallet:
        """
        Insert a new wallet with zero balance. Uses an atomic upsert
        to handle race conditions gracefully.
        """
        from sqlalchemy.dialects.postgresql import insert

        stmt = (
            insert(Wallet)
            .values(user_id=user_id, currency=currency, balance=0, status="active")
            .on_conflict_do_nothing(index_elements=["user_id", "currency"])
            .returning(Wallet)
        )

        result = await db.execute(stmt)
        wallet = result.scalar_one_or_none()

        if not wallet:
            # Another concurrent request created it just now. Fetch it.
            stmt_get = select(Wallet).where(
                Wallet.user_id == user_id,
                Wallet.currency == currency,
            )
            res = await db.execute(stmt_get)
            wallet = res.scalar_one_or_none()

        return wallet

    # =====================================================================
    # Read
    # =====================================================================

    @staticmethod
    async def get_wallet_by_id(
        db: AsyncSession,
        wallet_id: str,
    ) -> Wallet | None:
        """
        Fetch a single wallet by its UUID primary key.
        Returns None if not found.
        """
        stmt = select(Wallet).where(Wallet.id == wallet_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_wallets_by_user(
        db: AsyncSession,
        user_id: str,
    ) -> list[Wallet]:
        """
        Fetch all wallets belonging to a user.

        Returns an empty list if the user has no wallets.
        Ordered by creation date (oldest first).
        """
        stmt = (
            select(Wallet).where(Wallet.user_id == user_id).order_by(Wallet.created_at)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_wallet_by_user_and_currency(
        db: AsyncSession,
        user_id: str,
        currency: str,
    ) -> Wallet | None:
        """
        Look up a user's wallet for a specific currency.

        Used by:
        - Service layer to check for duplicates before creation.
        - Transfer service to find sender/receiver wallets.

        Returns None if the user has no wallet in that currency.
        The unique constraint (uq_user_currency) guarantees at most
        one result.
        """
        stmt = select(Wallet).where(
            Wallet.user_id == user_id,
            Wallet.currency == currency,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # =====================================================================
    # Update
    # =====================================================================

    @staticmethod
    async def update_wallet_status(
        db: AsyncSession,
        wallet_id: str,
        new_status: str,
    ) -> None:
        """
        Update a wallet's status (active, frozen, closed).

        Note: this does NOT update the balance. Balance changes
        go exclusively through the ledger repository (Phase 8).
        """
        stmt = update(Wallet).where(Wallet.id == wallet_id).values(status=new_status)
        await db.execute(stmt)
