"""
Ledger Pydantic schemas — request/response validation.

These schemas define the data contracts for ledger operations:

- LedgerOperation:   a single debit or credit instruction (input).
- TransactionCreate: a batch of operations to execute atomically (input).
- LedgerEntryRead:   a single ledger entry returned to clients (output).
- TransactionRead:   a transaction with all its entries (output).

The key design:
  The caller (e.g., TransferService) constructs a list of LedgerOperations
  and passes them to the LedgerService. The LedgerService validates the
  zero-sum property and executes them atomically.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class LedgerOperation(BaseModel):
    """
    A single debit or credit instruction.

    This is the INPUT format — what the caller sends to the ledger.
    It describes ONE leg of a transaction:
      "debit 5000 from wallet X"  or  "credit 5000 to wallet Y"

    The ledger service receives a LIST of these operations and
    executes them atomically as a single transaction.
    """

    wallet_id: uuid.UUID = Field(
        ...,
        description="The wallet to debit or credit.",
    )
    entry_type: str = Field(
        ...,
        description="'debit' (money out) or 'credit' (money in).",
    )
    amount: int = Field(
        ...,
        gt=0,
        description="Amount in minor units (cents/paise). Must be positive.",
    )

    @field_validator("entry_type")
    @classmethod
    def validate_entry_type(cls, v: str) -> str:
        """Ensure entry_type is 'debit' or 'credit'."""
        v = v.lower()
        if v not in {"debit", "credit"}:
            msg = "entry_type must be 'debit' or 'credit'."
            raise ValueError(msg)
        return v


class TransactionCreate(BaseModel):
    """
    Request to execute a ledger transaction.

    Contains:
    - transaction_type: categorizes the business event.
    - description: human-readable summary.
    - reference_id: optional external reference for idempotency.
    - operations: list of debit/credit operations (must be zero-sum).

    The zero-sum property (∑ credits == ∑ debits) is verified by
    the ledger repository BEFORE any database writes.
    """

    transaction_type: str = Field(
        ...,
        description="Type: 'p2p_transfer', 'deposit', 'withdrawal', 'fee', 'refund'.",
    )
    description: str | None = Field(
        None,
        description="Human-readable description.",
    )
    reference_id: str | None = Field(
        None,
        description="External reference for tracing/idempotency.",
    )
    operations: list[LedgerOperation] = Field(
        ...,
        min_length=2,
        description="At least 2 operations (debit + credit). Must be zero-sum.",
    )


class LedgerEntryRead(BaseModel):
    """A single ledger entry returned to clients."""

    id: uuid.UUID
    transaction_id: uuid.UUID
    wallet_id: uuid.UUID
    entry_type: str
    amount: int
    amount_display: str = "0.00"
    balance_after: int
    balance_after_display: str = "0.00"
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_entry(cls, entry) -> "LedgerEntryRead":
        """Create from ORM instance with formatted display fields."""
        return cls(
            id=entry.id,
            transaction_id=entry.transaction_id,
            wallet_id=entry.wallet_id,
            entry_type=entry.entry_type,
            amount=entry.amount,
            amount_display=f"{entry.amount / 100:.2f}",
            balance_after=entry.balance_after,
            balance_after_display=f"{entry.balance_after / 100:.2f}",
            created_at=entry.created_at,
        )


class TransactionRead(BaseModel):
    """A transaction with all its ledger entries."""

    id: uuid.UUID
    transaction_type: str
    description: str | None
    reference_id: str | None
    status: str
    entries: list[LedgerEntryRead]
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_transaction(cls, txn) -> "TransactionRead":
        """Create from ORM Transaction with eager-loaded entries."""
        return cls(
            id=txn.id,
            transaction_type=txn.transaction_type,
            description=txn.description,
            reference_id=txn.reference_id,
            status=txn.status,
            entries=[LedgerEntryRead.from_entry(e) for e in txn.entries],
            created_at=txn.created_at,
        )
