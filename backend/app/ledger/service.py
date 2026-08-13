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

from datetime import datetime

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

        # Eagerly load the transaction with its entries to avoid lazy-loading crashes
        txn_with_entries = await LedgerRepository.get_transaction_by_id(db, str(txn.id))
        
        return TransactionRead.from_transaction(txn_with_entries)

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
    async def get_wallet_transaction_detail(
        db: AsyncSession,
        wallet_id: str,
        transaction_id: str,
    ) -> TransactionRead:
        """
        Fetch full details of a transaction, ensuring it involves the specified wallet.
        """
        from fastapi import HTTPException, status

        txn = await LedgerRepository.get_transaction_by_id(db, transaction_id)
        if not txn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found."
            )

        # Ensure the wallet is involved in this transaction
        is_involved = any(str(entry.wallet_id) == wallet_id for entry in txn.entries)
        if not is_involved:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Transaction does not belong to this wallet.",
            )

        return TransactionRead.from_transaction(txn)

    @staticmethod
    async def get_wallet_history(
        db: AsyncSession,
        wallet_id: str,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
        status_filter: str | None = None,
        transaction_type: str | None = None,
        entry_type: str | None = None,
        min_amount: int | None = None,
        max_amount: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
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
            search=search,
            status_filter=status_filter,
            transaction_type=transaction_type,
            entry_type=entry_type,
            min_amount=min_amount,
            max_amount=max_amount,
            start_date=start_date,
            end_date=end_date,
        )
        return [
            {
                "id": str(e.id),
                "transaction_id": str(e.transaction_id),
                "transaction_type": e.transaction.transaction_type
                if e.transaction
                else "unknown",
                "status": e.transaction.status if e.transaction else "unknown",
                "reference_id": e.transaction.reference_id if e.transaction else None,
                "description": e.transaction.description if e.transaction else None,
                "entry_type": e.entry_type,
                "amount": e.amount,
                "amount_display": f"{e.amount / 100:.2f}",
                "balance_after": e.balance_after,
                "balance_after_display": f"{e.balance_after / 100:.2f}",
                "created_at": e.created_at.isoformat(),
            }
            for e in entries
        ]

    @staticmethod
    async def create_transaction_intent(
        db: AsyncSession,
        transaction_type: str,
        operations: list[LedgerOperation],
        description: str | None = None,
        reference_id: str | None = None,
    ) -> TransactionRead:
        """Create a pending transaction without moving money."""
        txn = await LedgerRepository.create_transaction_intent(
            db=db,
            transaction_type=transaction_type,
            operations=operations,
            description=description,
            reference_id=reference_id,
        )
        return TransactionRead.from_transaction(txn)

    @staticmethod
    async def update_transaction_status(
        db: AsyncSession,
        transaction_id: str,
        new_status: str,
    ) -> TransactionRead:
        """Safely transition a transaction's status."""
        txn = await LedgerRepository.update_transaction_status(
            db, transaction_id, new_status
        )
        return TransactionRead.from_transaction(txn)

    @staticmethod
    async def commit_async_transaction(
        db: AsyncSession,
        transaction_id: str,
    ) -> TransactionRead:
        """Finalize a pending/processing transaction, execute ledger entries, update balances."""
        txn = await LedgerRepository.commit_async_transaction(db, transaction_id)
        return TransactionRead.from_transaction(txn)

    @staticmethod
    async def reverse_transaction(
        db: AsyncSession,
        transaction_id: str,
        reason: str | None = None,
    ) -> TransactionRead:
        """
        Reverse a completed transaction.

        Creates a new transaction with swapped debits/credits to balance
        out the original operations, and marks the original as 'reversed'.
        """
        from fastapi import HTTPException, status

        # 1. Fetch original transaction
        original_txn = await LedgerRepository.get_transaction_by_id(db, transaction_id)
        if not original_txn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original transaction not found.",
            )

        if original_txn.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only 'completed' transactions can be reversed. Current status: {original_txn.status}",
            )

        if original_txn.transaction_type == "reversal":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reverse a reversal transaction.",
            )

        # 2. Construct compensating operations
        compensating_ops = []
        for entry in original_txn.entries:
            new_type = "credit" if entry.entry_type == "debit" else "debit"
            compensating_ops.append(
                LedgerOperation(
                    wallet_id=entry.wallet_id, entry_type=new_type, amount=entry.amount
                )
            )

        desc = f"Reversal of {transaction_id}"
        if reason:
            desc += f": {reason}"

        # 3. Execute the compensating transaction atomically
        reversal_txn = await LedgerRepository.execute_transaction(
            db=db,
            transaction_type="reversal",
            operations=compensating_ops,
            description=desc,
            reference_id=f"rev_{transaction_id}",
        )

        # 4. Mark original as reversed
        await LedgerRepository.update_transaction_status(db, transaction_id, "reversed")

        return TransactionRead.from_transaction(reversal_txn)
