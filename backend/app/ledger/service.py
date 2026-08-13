"""
Ledger service — business logic wrapper for the transaction engine.

This thin service layer wraps the LedgerRepository and provides:
1. A clean API for other services (TransferService, etc.) to execute
   ledger transactions without knowing the repository internals.
2. Transaction history retrieval with formatted output.
3. Commit management — the repository flushes, the service commits.

Why is this layer thin?
The heavy lifting (locking, verification, atomicity) is in the repository.
This service is intentionally minimal — it's a coordination layer,
not a business logic layer. The actual business rules (e.g., "can this
user transfer to that user?") live in the domain services (TransferService).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.ledger.repository import LedgerRepository
from app.ledger.schemas import LedgerOperation, TransactionRead


class LedgerService:
    """
    Ledger operations — execute transactions and retrieve history.
    """

    @staticmethod
    async def execute_transaction(
        db: AsyncSession,
        transaction_type: str,
        operations: list[LedgerOperation],
        description: str | None = None,
        reference_id: str | None = None,
    ) -> TransactionRead:
        """
        Execute a double-entry transaction and commit.

        This is the single entry point for ALL balance changes.
        Every money movement in the system flows through here.

        Args:
            db: Async database session.
            transaction_type: e.g., "p2p_transfer", "deposit", "withdrawal".
            operations: List of debit/credit operations (must be zero-sum).
            description: Human-readable summary.
            reference_id: External reference for tracing.

        Returns:
            TransactionRead with all ledger entries.
        """
        txn = await LedgerRepository.execute_transaction(
            db=db,
            transaction_type=transaction_type,
            operations=operations,
            description=description,
            reference_id=reference_id,
        )

        await db.commit()
        await db.refresh(txn)

        return TransactionRead.from_transaction(txn)

    @staticmethod
    async def get_transaction(
        db: AsyncSession,
        transaction_id: str,
    ) -> TransactionRead | None:
        """Fetch a transaction by ID with its entries."""
        txn = await LedgerRepository.get_transaction_by_id(db, transaction_id)
        if txn is None:
            return None
        return TransactionRead.from_transaction(txn)

    @staticmethod
    async def get_wallet_history(
        db: AsyncSession,
        wallet_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """
        Fetch ledger entries for a wallet (newest first).

        Returns a list of dicts with formatted amounts for display.
        """
        entries = await LedgerRepository.get_wallet_entries(
            db=db,
            wallet_id=wallet_id,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "id": str(e.id),
                "transaction_id": str(e.transaction_id),
                "entry_type": e.entry_type,
                "amount": e.amount,
                "amount_display": f"{e.amount / 100:.2f}",
                "balance_after": e.balance_after,
                "balance_after_display": f"{e.balance_after / 100:.2f}",
                "created_at": e.created_at.isoformat(),
            }
            for e in entries
        ]
