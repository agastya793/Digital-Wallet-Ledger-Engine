"""
Wallet database model.

Represents a monetary account belonging to a user. Each wallet holds
a single currency and tracks its balance in minor units (BIGINT).

Design decisions documented in Phase 1:
- BIGINT balance: $10.50 = 1050 (cents). Never floats.
- One wallet per currency per user (enforced at service layer).
- Balance is a cached value — the source of truth is ledger_entries.
- Status field allows freezing wallets for fraud/compliance.

Table relationships:
    users (1) ──→ (N) wallets
    wallets (1) ──→ (N) ledger_entries   (Phase 8)
"""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Wallet(Base, UUIDMixin, TimestampMixin):
    """
    Monetary wallet — one per currency per user.

    Balance semantics:
    - Stored as BIGINT in minor units (cents, paise, etc.).
    - $100.00 USD = balance 10000.
    - ₹500.75 INR = balance 50075.
    - This eliminates ALL floating-point rounding errors.
    - Balance is updated atomically alongside ledger entries in Phase 8.

    Status values:
    - "active":  normal operations allowed.
    - "frozen":  no transactions allowed (fraud hold, compliance review).
    - "closed":  permanently deactivated (balance must be 0).
    """

    __tablename__ = "wallets"

    # ---- Constraints ----
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "currency",
            name="uq_user_currency",
            # Without this, a user could create multiple USD wallets.
            # That would make transfers ambiguous ("which USD wallet?").
        ),
        CheckConstraint(
            "balance >= 0",
            name="chk_wallet_balance_positive",
        ),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        # Index: fast lookup of all wallets for a user.
        # CASCADE: if user is deleted, their wallets are deleted.
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        # ISO 4217 currency code: USD, EUR, INR, etc.
        # Validated at API layer (Pydantic schema) to be exactly 3 uppercase chars.
    )

    balance: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        # BIGINT range: -9.2 quintillion to +9.2 quintillion.
        # At 2 decimal places, this supports up to ~92 quadrillion dollars.
        # More than enough for any real-world wallet system.
        #
        # Default 0: new wallets start with zero balance.
        # Balance is ONLY modified via ledger operations (Phase 8).
        # There is NO direct "update balance" endpoint or service method.
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        # String instead of SQL ENUM to avoid migration pain when
        # adding new statuses. Validation is at the Pydantic layer.
    )

    # ---- Relationships ----
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="wallets",
    )

    def __repr__(self) -> str:
        return f"<Wallet {self.currency} balance={self.balance} status={self.status}>"
