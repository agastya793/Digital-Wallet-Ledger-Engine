"""
Wallet Pydantic schemas — request/response validation.

Schemas:
- WalletCreate:  create a new wallet (specify currency only).
- WalletRead:    wallet data returned to clients (includes formatted balance).
- WalletUpdate:  update wallet status (freeze/unfreeze).

Balance display:
    Internally, balance is stored as BIGINT minor units (e.g., 1050 = $10.50).
    The API returns BOTH the raw integer AND a human-readable string:
        { "balance": 1050, "balance_display": "10.50" }
    This gives consumers flexibility — use the integer for math,
    the string for display.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class WalletCreate(BaseModel):
    """
    Request payload to create a new wallet.

    Only the currency is required — balance starts at 0,
    status starts at "active", user is extracted from the JWT.
    """

    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code (e.g., USD, EUR, INR).",
        examples=["USD", "EUR", "INR"],
    )

    @field_validator("currency")
    @classmethod
    def validate_currency_code(cls, v: str) -> str:
        """
        Enforce uppercase 3-letter currency code.

        We normalize to uppercase so "usd" and "USD" are treated
        the same — prevents duplicate wallets due to case difference.
        """
        v = v.upper()
        if not v.isalpha() or len(v) != 3:
            msg = "Currency must be exactly 3 letters (e.g., USD, EUR)."
            raise ValueError(msg)
        return v


class WalletRead(BaseModel):
    """
    Wallet data returned to clients.

    Includes both the raw balance (integer minor units) and a
    formatted display string for convenience.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    currency: str
    balance: int
    balance_display: str = Field(
        default="0.00",
        description="Human-readable balance (e.g., '10.50').",
    )
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_wallet(cls, wallet) -> "WalletRead":
        """
        Create a WalletRead from a Wallet ORM instance.

        Computes balance_display from the raw integer balance.
        Assumes 2 decimal places (standard for most currencies).

        For zero-decimal currencies (JPY, KRW), this would need
        currency-specific formatting — a future enhancement.
        """
        balance_display = f"{wallet.balance / 100:.2f}"
        return cls(
            id=wallet.id,
            user_id=wallet.user_id,
            currency=wallet.currency,
            balance=wallet.balance,
            balance_display=balance_display,
            status=wallet.status,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at,
        )


class WalletDeposit(BaseModel):
    """
    Request payload to deposit money into a wallet in sandbox mode.
    """

    amount: float = Field(
        ...,
        gt=0,
        description="Amount to deposit in major units (e.g. 10.50). Must be positive.",
    )


class WalletUpdate(BaseModel):
    """
    Request payload to update a wallet.

    Currently only supports status changes (freeze/unfreeze).
    Balance changes are NEVER done via this endpoint — they go
    through the ledger system (Phase 8).
    """

    status: str = Field(
        ...,
        description="New wallet status: 'active', 'frozen', or 'closed'.",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Ensure status is a valid value."""
        allowed = {"active", "frozen", "closed"}
        if v not in allowed:
            msg = f"Status must be one of: {', '.join(sorted(allowed))}."
            raise ValueError(msg)
        return v
