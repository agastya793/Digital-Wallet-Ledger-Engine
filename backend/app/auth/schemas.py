"""
Authentication Pydantic schemas — request/response validation.

These schemas define the exact shape of data at the API boundary.
They enforce constraints (email format, password length, enum values)
before the data reaches the service or database layer.

Separation from SQLAlchemy models:
- Models define database structure (columns, FKs, indexes).
- Schemas define API contracts (what the client sends/receives).
- This separation lets us evolve the API independently of the DB.

Naming convention:
- *Create:  incoming data for creating a resource
- *Read:    outgoing data returned to the client
- *Update:  incoming data for modifying a resource
- *Request: incoming data for an action (not CRUD)
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# =============================================================================
# User Schemas
# =============================================================================


class UserCreate(BaseModel):
    """
    Registration request payload.

    Validation:
    - email: must be a valid email format (via email-validator package).
    - password: 8-128 chars. 8 is NIST minimum, 128 prevents hash-DoS
      (bcrypt truncates at 72 bytes, but we don't want megabyte passwords).
    - full_name: optional display name.
    """

    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password must be 8-128 characters.",
    )
    full_name: str | None = Field(
        None,
        max_length=255,
        description="Optional display name.",
    )


class UserRead(BaseModel):
    """
    User data returned to clients.

    Critically, this NEVER includes hashed_password.
    The `model_config` with `from_attributes=True` allows creating
    this schema directly from a SQLAlchemy User model instance.
    """

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
    # from_attributes=True: enables UserRead.model_validate(user_orm_instance)
    # This replaces Pydantic v1's `orm_mode = True`.


# =============================================================================
# Token Schemas
# =============================================================================


class Token(BaseModel):
    """
    Token pair returned on login and refresh.

    access_token:  short-lived JWT for API access (15 min default).
    refresh_token: long-lived opaque string for getting new access tokens.
    token_type:    always "bearer" per OAuth2 spec.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """
    Decoded JWT access token payload.

    Used internally to extract claims from verified tokens.
    Not exposed to clients directly.
    """

    sub: str  # subject (user UUID)
    role: str = "user"
    type: str = "access"


class RefreshTokenRequest(BaseModel):
    """
    Request body for the /refresh endpoint.

    The client sends the raw refresh token it received during login.
    We hash it and look up the hash in the database.
    """

    refresh_token: str = Field(
        ...,
        description="The refresh token received from login or previous refresh.",
    )
