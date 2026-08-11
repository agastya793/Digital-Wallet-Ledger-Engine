"""
Merchant Pydantic schemas — request/response validation.

Schemas for the merchant payment gateway:
- MerchantRegister:     register as a merchant.
- MerchantRead:         merchant profile returned to clients.
- CheckoutCreate:       create a payment request.
- CheckoutRead:         checkout session returned to clients.
- CheckoutPayRequest:   customer pays a checkout session.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator


class MerchantRegister(BaseModel):
    """
    Request to register as a merchant.

    The user must already be registered (Phase 6 auth).
    This upgrades their account with a merchant profile.
    """

    business_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the business.",
    )
    webhook_url: str | None = Field(
        None,
        description="URL to receive payment notifications (POST).",
    )


class MerchantRegisterResponse(BaseModel):
    """
    Response after merchant registration.

    CRITICAL: `api_key` is returned exactly ONCE. It is never
    stored in plaintext and cannot be retrieved again.
    The merchant must save it immediately.
    """

    merchant_id: uuid.UUID
    business_name: str
    api_key: str = Field(
        ...,
        description="Your API key. Save it now — it cannot be retrieved again.",
    )
    message: str = "Store your API key securely. It will not be shown again."


class MerchantRead(BaseModel):
    """Merchant profile returned to clients (no API key)."""

    id: uuid.UUID
    user_id: uuid.UUID
    business_name: str
    webhook_url: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CheckoutCreate(BaseModel):
    """
    Request to create a checkout session.

    The merchant's server sends this via API key auth.
    It represents a payment request for a specific amount.
    """

    amount: int = Field(
        ...,
        gt=0,
        description="Amount in minor units (e.g., 5000 = $50.00).",
    )
    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code.",
    )
    description: str | None = Field(
        None,
        max_length=500,
        description="What the customer is paying for.",
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v = v.upper()
        if not v.isalpha() or len(v) != 3:
            msg = "Currency must be exactly 3 letters."
            raise ValueError(msg)
        return v


class CheckoutRead(BaseModel):
    """Checkout session data returned to clients."""

    id: uuid.UUID
    merchant_id: uuid.UUID
    amount: int
    amount_display: str = "0.00"
    currency: str
    description: str | None
    status: str
    paid_by_user_id: uuid.UUID | None
    paid_at: datetime | None
    transaction_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_session(cls, session) -> "CheckoutRead":
        return cls(
            id=session.id,
            merchant_id=session.merchant_id,
            amount=session.amount,
            amount_display=f"{session.amount / 100:.2f}",
            currency=session.currency,
            description=session.description,
            status=session.status,
            paid_by_user_id=session.paid_by_user_id,
            paid_at=session.paid_at,
            transaction_id=session.transaction_id,
            created_at=session.created_at,
        )


class CheckoutPayRequest(BaseModel):
    """
    Request from a customer to pay a checkout session.

    The customer provides the checkout session ID.
    The system handles wallet lookup and fund transfer.
    """

    session_id: uuid.UUID = Field(
        ...,
        description="The checkout session ID to pay.",
    )
