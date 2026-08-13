"""
Authentication database models — User and RefreshToken.

These models represent the core identity and session management tables.

Table relationships:
    users (1) ──→ (N) refresh_tokens
    A user can have multiple active refresh tokens (e.g., logged in on
    phone + laptop simultaneously).

Design notes:
- User.hashed_password:  bcrypt hash, NEVER plaintext.
- User.role:             "user" or "admin" — used for RBAC in dependencies.
- User.is_active:        soft-delete flag. Deactivated users can't login
                          but their data is preserved for audit trails.
- RefreshToken.hashed_token:  SHA-256 of the opaque token. The raw token
                               is only ever held by the client.
- RefreshToken has NO updated_at:  tokens are immutable once created.
                                    They are either active or revoked.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    """
    Application user account.

    Stores identity (email), credentials (hashed_password),
    authorization level (role), and account status (is_active).
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        # Index on email: O(log n) lookups for login and duplicate checks.
        # Without index: every login does a full table scan.
    )

    hashed_password: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        # Text instead of String(N): bcrypt hashes are ~60 chars today,
        # but if we migrate to argon2 they can be longer. Text is future-proof.
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        # Optional — not everyone provides a name at registration.
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="user",
        # Valid values: "user", "admin".
        # We use a string instead of an enum to avoid migration headaches
        # when adding new roles. Validation happens in the Pydantic schema.
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        # Soft-delete: setting is_active=False disables login
        # without destroying data. Required for financial audit trails.
    )

    # ---- Relationships ----
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        # cascade="all, delete-orphan": deleting a user also deletes
        # all their refresh tokens. No orphaned tokens in the DB.
        # lazy="selectin": eager-load tokens in a single query when
        # we access user.refresh_tokens. Prevents N+1 queries.
    )

    wallets: Mapped[list["Wallet"]] = relationship(  # noqa: F821
        "Wallet",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        # Same pattern as refresh_tokens — deleting a user cascades
        # to all their wallets. selectin avoids N+1 queries.
    )

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role} active={self.is_active}>"


class RefreshToken(Base, UUIDMixin):
    """
    Refresh token record — maps a hashed opaque token to a user.

    Lifecycle:
    1. Created on login or token refresh (with fresh expiration).
    2. Used once on /refresh (then revoked, new token issued → rotation).
    3. Expired tokens are candidates for cleanup via scheduled job.

    Security properties:
    - Only the SHA-256 hash is stored. Raw token stays with the client.
    - is_revoked: set to True on use (rotation) or explicit logout.
    - expires_at: hard expiration regardless of revocation status.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        # Index: fast lookup of all tokens for a user (e.g., "revoke all").
        # CASCADE: if user is deleted, their tokens are auto-deleted.
    )

    hashed_token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        # SHA-256 hex digest is always 64 characters.
        # Unique + indexed: fast lookup during /refresh.
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        # Manually defined instead of using TimestampMixin because
        # refresh tokens are immutable — no updated_at needed.
        # Adding updated_at would imply tokens can be modified,
        # which contradicts the security model.
    )

    # ---- Relationships ----
    user: Mapped["User"] = relationship(
        "User",
        back_populates="refresh_tokens",
    )

    def __repr__(self) -> str:
        return f"<RefreshToken user_id={self.user_id} revoked={self.is_revoked}>"
