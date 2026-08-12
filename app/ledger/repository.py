"""
Ledger repository — the ACID transaction engine.

This is the most critical module in the entire system. It guarantees:

1. **Atomicity**: All operations in a transaction succeed or fail together.
   No partial balance updates. Ever.

2. **Consistency**: Zero-sum verification ensures ∑ credits == ∑ debits.
   The system cannot create or destroy money.

3. **Isolation**: Pessimistic locking (SELECT FOR UPDATE) prevents
   concurrent transactions from seeing stale balances.

4. **Durability**: PostgreSQL's WAL ensures committed transactions
   survive crashes.

The core method is `execute_transaction()`. It:
1. Validates zero-sum property.
2. Sorts wallet IDs (deadlock prevention).
3. Locks wallets with SELECT FOR UPDATE.
4. Verifies sufficient funds for debits.
5. Inserts the Transaction record.
6. Inserts LedgerEntry records.
7. Updates wallet balances.
8. All within a single savepoint (begin_nested).

If ANY step fails, the entire savepoint is rolled back.
"""

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ledger.models import LedgerEntry, Transaction
from app.ledger.schemas import LedgerOperation
from app.wallet.models import Wallet


class LedgerRepository:
    """
    Double-entry accounting engine.

    All methods are static. The session is always passed in.
    """

    @staticmethod
    async def execute_transaction(
        db: AsyncSession,
        transaction_type: str,
        operations: list[LedgerOperation],
        description: str | None = None,
        reference_id: str | None = None,
    ) -> Transaction:
        """
        Execute a double-entry transaction atomically.

        This is the ONLY method that modifies wallet balances.
        No other code in the system is allowed to update balances directly.

        Args:
            db: Async database session.
            transaction_type: Business event type (e.g., "p2p_transfer").
            operations: List of debit/credit operations. Must be zero-sum.
            description: Optional human-readable summary.
            reference_id: Optional external reference.

        Returns:
            The created Transaction with all its LedgerEntries.

        Raises:
            HTTPException 400: If operations are not zero-sum.
            HTTPException 400: If insufficient funds for a debit.
            HTTPException 404: If a wallet doesn't exist.
        """

        # =====================================================================
        # Step 1: Zero-Sum Verification
        # =====================================================================
        # The fundamental accounting equation: money in = money out.
        # If someone is debited $50, someone else must be credited $50.
        # This prevents the system from creating or destroying money.
        # =====================================================================
        total_debits = sum(op.amount for op in operations if op.entry_type == "debit")
        total_credits = sum(op.amount for op in operations if op.entry_type == "credit")

        if total_debits != total_credits:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Transaction is not zero-sum. "
                    f"Debits: {total_debits}, Credits: {total_credits}."
                ),
            )

        # =====================================================================
        # Step 2: Deadlock Prevention — Sort Wallet IDs
        # =====================================================================
        # If Transaction A locks Wallet 1 then Wallet 2, and Transaction B
        # locks Wallet 2 then Wallet 1, they deadlock (each waiting for the
        # other's lock). Sorting ensures ALL transactions lock wallets in
        # the same order → deadlocks are impossible.
        # =====================================================================
        unique_wallet_ids = sorted({str(op.wallet_id) for op in operations})

        # =====================================================================
        # Step 3: Begin Savepoint (Nested Transaction)
        # =====================================================================
        # begin_nested() creates a SAVEPOINT in PostgreSQL.
        # If anything fails inside, only this savepoint is rolled back,
        # not the entire session. The caller can still commit other work.
        # =====================================================================
        async with db.begin_nested():

            # =================================================================
            # Step 4: Lock Wallets (SELECT FOR UPDATE)
            # =================================================================
            # Pessimistic locking: no other transaction can read or modify
            # these wallets until we commit/rollback.
            # This prevents the "lost update" problem:
            #   T1 reads balance=100, T2 reads balance=100,
            #   T1 writes 50, T2 writes 50 → balance=50 (should be 0).
            # =================================================================
            locked_wallets: dict[str, Wallet] = {}
            for wallet_id in unique_wallet_ids:
                stmt = (
                    select(Wallet)
                    .where(Wallet.id == wallet_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                    # populate_existing=True is CRITICAL here!
                    # Without it, if the wallet was queried earlier in the 
                    # same request, SQLAlchemy will return the stale cached 
                    # balance instead of the fresh locked row from Postgres!
                )
                result = await db.execute(stmt)
                wallet = result.scalar_one_or_none()

                if wallet is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Wallet {wallet_id} not found.",
                    )

                if wallet.status != "active":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Wallet {wallet_id} is {wallet.status}. Cannot transact.",
                    )

                locked_wallets[str(wallet.id)] = wallet

            # =================================================================
            # Step 5: Verify Sufficient Funds for Debits
            # =================================================================
            for op in operations:
                if op.entry_type == "debit":
                    wallet = locked_wallets[str(op.wallet_id)]
                    if wallet.balance < op.amount:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                f"Insufficient funds in wallet {op.wallet_id}. "
                                f"Available: {wallet.balance / 100:.2f}, "
                                f"Required: {op.amount / 100:.2f}."
                            ),
                        )

            # =================================================================
            # Step 6: Create Transaction Record
            # =================================================================
            txn = Transaction(
                transaction_type=transaction_type,
                description=description,
                reference_id=reference_id,
                status="completed",
            )
            db.add(txn)
            await db.flush()  # Get txn.id without committing

            # =================================================================
            # Step 7: Create Ledger Entries + Update Balances
            # =================================================================
            for op in operations:
                wallet = locked_wallets[str(op.wallet_id)]

                # Calculate new balance
                if op.entry_type == "debit":
                    new_balance = wallet.balance - op.amount
                else:  # credit
                    new_balance = wallet.balance + op.amount

                # Create immutable ledger entry
                entry = LedgerEntry(
                    transaction_id=str(txn.id),
                    wallet_id=str(op.wallet_id),
                    entry_type=op.entry_type,
                    amount=op.amount,
                    balance_after=new_balance,
                )
                db.add(entry)

                # Update cached balance on wallet
                stmt = (
                    update(Wallet)
                    .where(Wallet.id == str(op.wallet_id))
                    .values(balance=new_balance)
                )
                res = await db.execute(stmt)
                if res.rowcount != 1:
                    raise RuntimeError(f"CRITICAL: Failed to update wallet {op.wallet_id}! Rowcount was {res.rowcount}.")

                # Update in-memory cache for subsequent operations
                # (important when multiple ops hit the same wallet)
                wallet.balance = new_balance

            await db.flush()

        # Transaction and entries are now flushed but NOT committed.
        # The caller (service layer) is responsible for committing.
        return txn

    @staticmethod
    async def get_transaction_by_id(
        db: AsyncSession,
        transaction_id: str,
    ) -> Transaction | None:
        """Fetch a transaction with its entries by ID."""
        stmt = select(Transaction).where(Transaction.id == transaction_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_wallet_entries(
        db: AsyncSession,
        wallet_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LedgerEntry]:
        """
        Fetch ledger entries for a wallet, newest first.

        Paginated to avoid loading thousands of entries at once.
        Default limit of 50 matches common API pagination patterns.
        """
        stmt = (
            select(LedgerEntry)
            .where(LedgerEntry.wallet_id == wallet_id)
            .order_by(LedgerEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
