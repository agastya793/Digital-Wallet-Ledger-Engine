"""
Ledger database models — Transaction and LedgerEntry.

This is the financial heart of the system. Every money movement
is recorded as a double-entry transaction:

    Transaction (1) ──→ (N) LedgerEntry

A Transaction groups related entries. Each entry is a single
debit or credit against a wallet. The fundamental rule:

    ∑ credits = ∑ debits   (zero-sum)

Example: User A sends $50 to User B:
    Transaction: "P2P Transfer"
    ├── LedgerEntry: debit  $50 from Wallet A
    └── LedgerEntry: credit $50 to   Wallet B

Design principles (from Phase 1):
- LedgerEntry is IMMUTABLE. No updated_at column. No UPDATE/DELETE
  operations in the repository. Once written, entries are permanent.
- If a transaction needs to be "reversed", a NEW compensating
  transaction is created (debit ↔ credit swapped).
- Balance on the wallet table is a CACHE. The source of truth is
  always the sum of ledger entries for that wallet.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Transaction(Base, UUIDMixin, TimestampMixin):
    """
    Groups related ledger entries into a single business event.

    Every financial operation (transfer, deposit, withdrawal, fee)
    creates exactly one Transaction with two or more LedgerEntries.

    Fields:
    - transaction_type: categorizes the business event.
    - description: human-readable summary.
    - reference_id: optional external reference (e.g., payment gateway ID).
    - status: "completed" (for now — future: "pending", "failed" for async flows).
    """

    __tablename__ = "transactions"

    transaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        # Values: "p2p_transfer", "deposit", "withdrawal", "fee", "refund"
        # String instead of ENUM for migration flexibility.
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        # Human-readable description, e.g., "Transfer from alice@example.com to bob@example.com"
    )

    reference_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        # External reference for tracing (idempotency key, payment gateway ID, etc.)
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="completed",
        # For synchronous transactions, status is always "completed".
        # Future async flows (bank transfers, pending approvals) may use
        # "pending" → "completed" / "failed".
    )

    # ---- Relationships ----
    entries: Mapped[list["LedgerEntry"]] = relationship(
        "LedgerEntry",
        back_populates="transaction",
        cascade="all, delete-orphan",
        lazy="selectin",
        # selectin: eager-load all entries when accessing transaction.entries.
        # A transaction typically has 2-4 entries — small enough to always load.
    )

    def __repr__(self) -> str:
        return f"<Transaction {self.transaction_type} status={self.status}>"


class LedgerEntry(Base, UUIDMixin):
    """
    A single debit or credit against a wallet.

    This is the IMMUTABLE source of truth for all balance changes.

    CRITICAL: This model intentionally has NO updated_at column.
    Ledger entries are append-only. Once created, they are NEVER
    modified or deleted. This is a fundamental accounting principle.

    Fields:
    - wallet_id: the wallet being debited or credited.
    - transaction_id: the parent transaction grouping this entry.
    - entry_type: "debit" (money out) or "credit" (money in).
    - amount: always POSITIVE. The sign is determined by entry_type.
    - balance_after: the wallet's balance AFTER this entry was applied.
      This is a snapshot for auditability — you can reconstruct the
      complete balance history by reading entries chronologically.

    Accounting convention:
    - DEBIT  = money leaving the wallet  (balance decreases)
    - CREDIT = money entering the wallet (balance increases)
    """

    __tablename__ = "ledger_entries"

    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    wallet_id: Mapped[str] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        # Index: fast lookup of all entries for a wallet (balance history).
    )

    entry_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        # "debit" or "credit". Validated at service/schema layer.
    )

    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        # ALWAYS positive. The direction (in/out) is determined by entry_type.
        # Storing amount as always-positive simplifies zero-sum verification:
        #   sum(credits) == sum(debits)  ← clean comparison, no sign confusion.
        #
        # Same BIGINT minor-unit convention as wallet.balance.
        # $10.50 = 1050.
    )

    balance_after: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        # Snapshot of wallet.balance AFTER this entry was applied.
        # Enables:
        # 1. Balance history: "What was my balance at 3pm yesterday?"
        # 2. Audit verification: walk entries and verify balance_after is consistent.
        # 3. Debugging: instantly see if a balance went negative.
    )

    # ---- Timestamp (manually, not via mixin) ----
    # We use created_at only. NO updated_at — entries are immutable.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ---- Relationships ----
    transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        back_populates="entries",
    )

    def __repr__(self) -> str:
        return (
            f"<LedgerEntry {self.entry_type} "
            f"amount={self.amount} "
            f"wallet={self.wallet_id}>"
        )
