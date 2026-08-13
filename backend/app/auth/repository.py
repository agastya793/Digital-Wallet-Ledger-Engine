"""
Authentication repository — data access layer.

This module owns ALL database I/O for the auth domain.
The service layer calls these methods — it never touches
SQLAlchemy directly. This separation gives us:

1. **Testability**: Service tests can mock the repository.
2. **Single Responsibility**: Repository = data access. Service = business logic.
3. **Query encapsulation**: If we switch from Postgres to DynamoDB,
   only this file changes. The service layer is untouched.

All methods accept an AsyncSession — they don't create or manage
sessions themselves. Session lifecycle is controlled by the caller
(typically the FastAPI dependency `get_db()`).
"""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken, User


class AuthRepository:
    """
    Data access methods for User and RefreshToken tables.

    Every method is a static/class method that takes a session parameter.
    We don't store session as instance state — this avoids accidentally
    sharing sessions across requests in concurrent async code.
    """

    # =====================================================================
    # User Queries
    # =====================================================================

    @staticmethod
    async def get_user_by_email(
        db: AsyncSession,
        email: str,
    ) -> User | None:
        """
        Look up a user by email address.

        Used by:
        - Registration: check if email is already taken.
        - Login: find user to verify password against.

        Returns None if no user exists with that email.
        The email index on the users table makes this O(log n).
        """
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(
        db: AsyncSession,
        user_id: str,
    ) -> User | None:
        """
        Look up a user by their UUID primary key.

        Used by:
        - get_current_user dependency: extract user_id from JWT, fetch user.
        - Any operation that needs the full User object from just an ID.
        """
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(
        db: AsyncSession,
        email: str,
        hashed_password: str,
        full_name: str | None = None,
    ) -> User:
        """
        Insert a new user into the database.

        The caller is responsible for:
        1. Hashing the password BEFORE calling this method.
        2. Checking for duplicate emails BEFORE calling this method.
        3. Committing the session AFTER calling this method.

        Why not commit here? Because the service layer may need to
        create a user AND a refresh token in a single transaction.
        """
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
        )
        db.add(user)
        await db.flush()
        # flush() sends the INSERT to the DB and populates user.id,
        # but does NOT commit. The transaction is still open.
        # This lets the service layer continue adding related records
        # (e.g., refresh token) in the same transaction.
        return user

    # =====================================================================
    # Refresh Token Queries
    # =====================================================================

    @staticmethod
    async def create_refresh_token(
        db: AsyncSession,
        user_id: str,
        hashed_token: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """
        Insert a new refresh token record.

        Stores only the SHA-256 hash of the token.
        The raw token is returned to the client by the service layer.
        """
        token_record = RefreshToken(
            user_id=user_id,
            hashed_token=hashed_token,
            expires_at=expires_at,
            created_at=datetime.now(UTC),
        )
        db.add(token_record)
        await db.flush()
        return token_record

    @staticmethod
    async def get_refresh_token_by_hash(
        db: AsyncSession,
        hashed_token: str,
    ) -> RefreshToken | None:
        """
        Look up a refresh token by its SHA-256 hash.

        Used during /refresh:
        1. Client sends raw token.
        2. Service hashes it.
        3. This method finds the matching DB record.

        Returns None if no token exists with that hash
        (token was never issued, or was already deleted).
        """
        stmt = select(RefreshToken).where(RefreshToken.hashed_token == hashed_token)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def revoke_refresh_token(
        db: AsyncSession,
        token_id: str,
    ) -> None:
        """
        Mark a refresh token as revoked.

        Called during:
        - Token rotation (old token is revoked after new one is issued).
        - Explicit logout.
        - Admin force-logout of a user.

        We set is_revoked=True rather than deleting the record.
        This preserves the audit trail of when tokens were issued and revoked.
        """
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(is_revoked=True)
        )
        await db.execute(stmt)

    @staticmethod
    async def revoke_all_user_tokens(
        db: AsyncSession,
        user_id: str,
    ) -> None:
        """
        Revoke ALL refresh tokens for a user.

        Used for:
        - "Log out everywhere" feature.
        - Account security incident (password change, suspicious activity).
        """
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
            )
            .values(is_revoked=True)
        )
        await db.execute(stmt)
