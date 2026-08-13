"""
Merchant database models — MerchantAccount and CheckoutSession.

This module enables the payment gateway functionality:

    MerchantAccount:
        A business registered on the platform. Authenticated via API key
        (X-API-Key header) instead of JWT. The API key is hashed before
        storage — the raw key is returned exactly once at registration.

    CheckoutSession:
        A payment request created by a merchant. A customer "pays" the
        session, which triggers a ledger transfer from the customer's
        wallet to the merchant's wallet.

Flow:
    1. Merchant registers → receives API key (one-time).
    2. Merchant creates checkout session (amount, currency).
    3. Customer pays session → funds move → webhook fires.

Table relationships:
    users (1) ──→ (1) merchant_accounts
    merchant_accounts (1) ──→ (N) checkout_sessions
    wallets are linked via user_id on the merchant account.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class MerchantAccount(Base, UUIDMixin, TimestampMixin):
    """
    A business account authorized to create checkout sessions.

    The dual-auth design:
    - As a USER: the merchant logs in with email/password (JWT).
    - As a MERCHANT: their server uses the API key (X-API-Key).

    This separation means a merchant's backend server never needs
    the owner's personal password — it uses the API key for
    machine-to-machine calls.
    """

    __tablename__ = "merchant_accounts"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        # unique: a user can only have ONE merchant account.
        # This is a 1:1 relationship.
    )

    business_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    hashed_api_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        # SHA-256 hash of the API key. The raw key is NEVER stored.
        # If the DB is compromised, the attacker can't use the hashes
        # to authenticate as the merchant.
    )

    webhook_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        # URL to POST payment notifications to.
        # Optional — not all merchants need webhooks.
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    # ---- Relationships ----
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        backref="merchant_account",
    )

    checkout_sessions: Mapped[list["CheckoutSession"]] = relationship(
        "CheckoutSession",
        back_populates="merchant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<MerchantAccount {self.business_name}>"


class CheckoutSession(Base, UUIDMixin, TimestampMixin):
    """
    A payment request created by a merchant.

    Lifecycle:
        1. "pending"  — merchant created it, waiting for customer payment.
        2. "paid"     — customer paid, funds transferred.
        3. "expired"  — TTL elapsed without payment (future enhancement).
        4. "cancelled" — merchant cancelled before payment.

    The checkout session ID is shared with the customer (via URL,
    QR code, etc.). The customer uses it to pay.
    """

    __tablename__ = "checkout_sessions"

    merchant_id: Mapped[str] = mapped_column(
        ForeignKey("merchant_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        # Amount in minor units, same convention as everywhere else.
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )

    paid_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        # SET NULL: if the paying user is deleted, we keep the session
        # record for audit but null out the reference.
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    transaction_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        # Links to the ledger Transaction created when payment was processed.
        # Enables tracing from checkout session → ledger entries.
    )

    # ---- Relationships ----
    merchant: Mapped["MerchantAccount"] = relationship(
        "MerchantAccount",
        back_populates="checkout_sessions",
    )

    def __repr__(self) -> str:
        return f"<CheckoutSession {self.currency} {self.amount} status={self.status}>"
