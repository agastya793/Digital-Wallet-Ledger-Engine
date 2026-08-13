"""
Authentication service — business logic layer.

This module sits between routes and repository. It contains all
authentication business logic:

1. **register_user**:     validate uniqueness → hash password → create user.
2. **authenticate_user**: verify email/password → issue token pair.
3. **refresh_access_token**: validate refresh token → rotate → issue new pair.

Business rules enforced here (NOT in the repository):
- Duplicate email detection (register_user)
- Password verification (authenticate_user)
- Token expiration and revocation checks (refresh_access_token)
- Token rotation (old refresh token is revoked when a new one is issued)

Error handling strategy:
- Service methods raise HTTPException directly. This is a pragmatic
  choice for a FastAPI monolith — the service IS the app boundary.
  In a microservice, you'd raise domain exceptions and map them in routes.
"""

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.repository import AuthRepository
from app.auth.schemas import Token
from app.auth.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.config import settings


class AuthService:
    """
    Authentication business logic.

    All methods are static — no instance state needed.
    Each method takes an AsyncSession and operates within it.
    """

    # =====================================================================
    # Registration
    # =====================================================================

    @staticmethod
    async def register_user(
        db: AsyncSession,
        email: str,
        password: str,
        full_name: str | None = None,
    ):
        """
        Register a new user account.

        Flow:
        1. Check if email is already taken → 409 Conflict.
        2. Hash the plaintext password with bcrypt.
        3. Create the user record in the database.
        4. Commit the transaction.
        5. Return the User ORM instance (for serialization to UserRead).

        Why 409 Conflict?
        RFC 9110 §15.5.10: "The request could not be processed because
        of conflict in the current state of the resource."
        A duplicate email IS a state conflict.
        """
        # 1. Uniqueness check
        existing = await AuthRepository.get_user_by_email(db, email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

        # 2. Hash password (bcrypt, ~250ms — intentionally slow)
        hashed = hash_password(password)

        # 3. Create user record
        user = await AuthRepository.create_user(
            db=db,
            email=email,
            hashed_password=hashed,
            full_name=full_name,
        )

        # 4. Commit — user is now persisted
        await db.commit()
        await db.refresh(user)
        # refresh() reloads the user from DB to get server-generated
        # values (created_at, updated_at from server_default).

        return user

    # =====================================================================
    # Login (Authentication)
    # =====================================================================

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str,
    ) -> Token:
        """
        Authenticate a user and issue a token pair.

        Flow:
        1. Look up user by email → 401 if not found.
        2. Verify password against stored bcrypt hash → 401 if wrong.
        3. Check if account is active → 403 if deactivated.
        4. Generate access token (JWT) and refresh token (opaque).
        5. Store hashed refresh token in database.
        6. Return the token pair.

        Security: steps 1 and 2 return the SAME generic error message.
        This prevents email enumeration attacks ("user not found" vs
        "wrong password" tells an attacker which emails are registered).
        """
        # 1-2. Look up user and verify password
        user = await AuthRepository.get_user_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
                # WWW-Authenticate header is required by RFC 6750 §3
                # when returning 401 for Bearer token auth.
            )

        # 3. Check account status
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account has been deactivated.",
            )

        # 4-5. Issue token pair
        token_pair = await AuthService._issue_token_pair(db, user)
        return token_pair

    # =====================================================================
    # Token Refresh
    # =====================================================================

    @staticmethod
    async def refresh_access_token(
        db: AsyncSession,
        raw_refresh_token: str,
    ) -> Token:
        """
        Exchange a valid refresh token for a new token pair.

        Implements **token rotation**:
        1. Hash the incoming refresh token.
        2. Look up the hash in the database → 401 if not found.
        3. Verify the token is not revoked → 401 if revoked.
        4. Verify the token is not expired → 401 if expired.
        5. Revoke the old refresh token.
        6. Issue a brand new access + refresh token pair.

        Why token rotation?
        If an attacker steals a refresh token and uses it AFTER the
        legitimate user has already used it, the stolen token is already
        revoked → attack fails. Without rotation, the stolen token
        would work until it expires (7 days!).
        """
        # 1. Hash the raw token
        hashed = hash_refresh_token(raw_refresh_token)

        # 2. Look up in database
        token_record = await AuthRepository.get_refresh_token_by_hash(db, hashed)
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 3. Check revocation
        if token_record.is_revoked:
            # If a revoked token is being used, it may indicate token theft.
            # Optionally: revoke ALL tokens for this user (security incident).
            await AuthRepository.revoke_all_user_tokens(db, token_record.user_id)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 4. Check expiration
        if token_record.expires_at < datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 5. Revoke the old token (rotation)
        await AuthRepository.revoke_refresh_token(db, str(token_record.id))

        # 6. Fetch the user and issue a new pair
        user = await AuthRepository.get_user_by_id(db, token_record.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is no longer active.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_pair = await AuthService._issue_token_pair(db, user)
        return token_pair

    # =====================================================================
    # Internal Helpers
    # =====================================================================

    @staticmethod
    async def _issue_token_pair(db: AsyncSession, user) -> Token:
        """
        Generate and persist a new access + refresh token pair.

        This is the shared logic between login and refresh.
        Extracted to avoid duplication.

        Steps:
        1. Create a JWT access token (stateless, not stored in DB).
        2. Generate a random refresh token (opaque string).
        3. Hash the refresh token and store the hash in the database.
        4. Commit the transaction.
        5. Return the Token schema with both tokens.
        """
        # 1. Access token (JWT)
        access_token = create_access_token(
            subject=str(user.id),
            role=user.role,
        )

        # 2. Refresh token (opaque)
        raw_refresh = generate_refresh_token()

        # 3. Store hashed refresh token
        refresh_expires = datetime.now(UTC) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        hashed_refresh = hash_refresh_token(raw_refresh)

        await AuthRepository.create_refresh_token(
            db=db,
            user_id=str(user.id),
            hashed_token=hashed_refresh,
            expires_at=refresh_expires,
        )

        # 4. Commit
        await db.commit()

        # 5. Return token pair (raw refresh token, NOT the hash)
        return Token(
            access_token=access_token,
            refresh_token=raw_refresh,
        )
