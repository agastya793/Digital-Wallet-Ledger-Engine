"""
Authentication dependencies — FastAPI dependency injection.

These are the "guards" that protect routes. Any route that needs
authentication adds one of these as a parameter:

    @router.get("/protected")
    async def protected_route(user: User = Depends(get_current_user)):
        return {"message": f"Hello, {user.email}"}

    @router.get("/admin-only")
    async def admin_route(user: User = Depends(get_current_admin)):
        return {"message": "You are an admin"}

How it works:
1. FastAPI extracts the Bearer token from the Authorization header.
2. get_current_user decodes the JWT and verifies the signature.
3. It fetches the user from the database using the "sub" claim.
4. If anything fails (expired, invalid, user not found), → 401.
5. get_current_admin wraps get_current_user and adds a role check.
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.repository import AuthRepository
from app.auth.schemas import TokenPayload
from app.config import settings
from app.database.dependencies import get_db

# ---- OAuth2 Scheme ----
# This tells FastAPI (and Swagger UI) that authentication uses
# Bearer tokens obtained from the /api/v1/auth/login endpoint.
# Swagger UI shows a "lock" icon and an authorization dialog.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    # tokenURL: the endpoint where Swagger UI sends credentials.
    # This doesn't affect the actual auth flow — it's purely for
    # the auto-generated API docs.
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and verify the current user from a JWT access token.

    This is the primary auth dependency. Add it to any route
    that requires authentication.

    Failure modes:
    - Token expired → 401 "Token has expired"
    - Token invalid/tampered → 401 "Could not validate credentials"
    - User ID from token doesn't match any DB record → 401
    - User account is deactivated → 401 "Account is deactivated"
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode and verify the JWT signature + expiration.
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        token_data = TokenPayload(**payload)

        # Verify this is an access token, not a refresh token.
        if token_data.type != "access":
            raise credentials_exception

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise credentials_exception

    # Fetch the user from the database.
    user = await AuthRepository.get_user_by_id(db, token_data.sub)
    if user is None:
        raise credentials_exception

    # Verify the account is still active.
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Verify the current user has admin role.

    This is a layered dependency — it first runs get_current_user
    to authenticate, then checks the role for authorization.

    Usage:
        @router.delete("/users/{id}")
        async def delete_user(admin: User = Depends(get_current_admin)):
            ...
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user
