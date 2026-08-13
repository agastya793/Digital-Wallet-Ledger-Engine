"""
Authentication API routes — /api/v1/auth/*.

Endpoints:
    POST /register  — Create a new user account.
    POST /login     — Authenticate and receive token pair.
    POST /refresh   — Exchange refresh token for new token pair.
    GET  /me        — Get the current authenticated user's profile.

All endpoints return consistent JSON. Error responses follow the
pattern established in Phase 1:
    {"detail": "Human-readable error message"}

OAuth2 compatibility:
    The /login endpoint uses OAuth2PasswordRequestForm (form data with
    "username" and "password" fields). This makes it compatible with:
    - FastAPI's Swagger UI authorization dialog
    - Standard OAuth2 client libraries
    We map "username" to "email" internally.
"""

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.auth.schemas import RefreshTokenRequest, Token, UserCreate, UserRead
from app.auth.service import AuthService
from app.database.dependencies import get_db

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        409: {"description": "Email already registered"},
    },
)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new user account.

    - **email**: Must be a valid email format. Must be unique.
    - **password**: Must be 8-128 characters.
    - **full_name**: Optional display name.

    Returns the created user profile (without password).
    """
    user = await AuthService.register_user(
        db=db,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
    )
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Login and receive tokens",
    responses={
        401: {"description": "Invalid credentials"},
        403: {"description": "Account deactivated"},
    },
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate with email and password, receive a token pair.

    Uses OAuth2 form format:
    - **username**: Your email address (OAuth2 spec uses "username").
    - **password**: Your password.

    Returns:
    - **access_token**: Short-lived JWT for API access (15 min).
    - **refresh_token**: Long-lived opaque token for renewal (7 days).
    - **token_type**: Always "bearer".
    """
    # OAuth2PasswordRequestForm uses "username" — we treat it as email.
    token_pair = await AuthService.authenticate_user(
        db=db,
        email=form_data.username,
        password=form_data.password,
    )
    return token_pair


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    responses={
        401: {"description": "Invalid, expired, or revoked refresh token"},
    },
)
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new token pair.

    Implements **token rotation**: the old refresh token is revoked
    and a completely new pair is issued. If a revoked token is
    presented, ALL tokens for that user are revoked as a security
    precaution (potential token theft detected).
    """
    token_pair = await AuthService.refresh_access_token(
        db=db,
        raw_refresh_token=body.refresh_token,
    )
    return token_pair


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Return the authenticated user's profile.

    Requires a valid access token in the Authorization header:
        Authorization: Bearer <access_token>
    """
    return current_user
