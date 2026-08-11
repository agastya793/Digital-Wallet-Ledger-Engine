"""
Transfer Pydantic schemas — request validation.

Defines the API contract for money transfers. The key UX decision:
transfers are addressed by recipient EMAIL, not UUID.

In a real wallet app, users don't know each other's UUIDs.
They know email addresses. This matches the UX of Venmo, PayPal,
Google Pay, etc.
"""

import uuid
from pydantic import BaseModel, EmailStr, Field, field_validator


class TransferRequest(BaseModel):
    """
    Request payload for a P2P (peer-to-peer) transfer.

    Example:
        {
            "recipient_email": "bob@example.com",
            "amount": 5000,
            "currency": "USD",
            "description": "Lunch money"
        }

    This transfers $50.00 USD (5000 minor units) from the
    authenticated user to bob@example.com.
    """

    recipient_email: EmailStr = Field(
        ...,
        description="Email address of the recipient.",
    )

    amount: int = Field(
        ...,
        gt=0,
        description=(
            "Amount to transfer in minor units (cents/paise). "
            "Must be positive. Example: 5000 = $50.00."
        ),
    )

    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code (e.g., USD, EUR, INR).",
        examples=["USD", "EUR", "INR"],
    )

    description: str | None = Field(
        None,
        max_length=500,
        description="Optional note for the transfer.",
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Normalize to uppercase and validate format."""
        v = v.upper()
        if not v.isalpha() or len(v) != 3:
            msg = "Currency must be exactly 3 letters (e.g., USD, EUR)."
            raise ValueError(msg)
        return v


class TransferResponse(BaseModel):
    """
    Response returned after a successful transfer.

    Includes the transaction ID for tracking and the formatted
    amount for display.
    """

    transaction_id: uuid.UUID
    sender_email: str
    recipient_email: str
    amount: int
    amount_display: str
    currency: str
    description: str | None
    status: str

    model_config = {"from_attributes": True}
