"""
Wallet API routes — /api/v1/wallets/*.

Endpoints:
    POST /          — Create a new wallet (specify currency).
    GET  /          — List all wallets for the authenticated user.
    GET  /{id}      — Get a specific wallet by ID.
    PATCH /{id}     — Update wallet status (freeze/unfreeze/close).

All endpoints require authentication (Bearer token).
Users can only access their own wallets — ownership is enforced
in the service layer.

Note: There is NO endpoint to directly modify balance.
Balance changes go exclusively through the ledger/transfer endpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.database.dependencies import get_db
from app.wallet.schemas import WalletCreate, WalletRead, WalletUpdate
from app.wallet.service import WalletService

router = APIRouter()


@router.post(
    "/",
    response_model=WalletRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new wallet",
    responses={
        409: {"description": "User already has a wallet in this currency"},
    },
)
async def create_wallet(
    body: WalletCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new wallet for the authenticated user.

    - **currency**: ISO 4217 currency code (e.g., USD, EUR, INR).
      Must be exactly 3 uppercase letters.

    Each user can have at most one wallet per currency.
    New wallets start with zero balance and "active" status.
    """
    return await WalletService.create_wallet(
        db=db,
        user=current_user,
        currency=body.currency,
    )


@router.get(
    "/",
    response_model=list[WalletRead],
    summary="List your wallets",
)
async def list_wallets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all wallets belonging to the authenticated user.

    Returns an empty list if the user has no wallets.
    """
    return await WalletService.get_user_wallets(
        db=db,
        user=current_user,
    )


@router.get(
    "/{wallet_id}",
    response_model=WalletRead,
    summary="Get a specific wallet",
    responses={
        404: {"description": "Wallet not found or doesn't belong to you"},
    },
)
async def get_wallet(
    wallet_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch a specific wallet by its ID.

    Returns 404 if the wallet doesn't exist OR doesn't belong to
    the authenticated user (prevents information leakage).
    """
    return await WalletService.get_wallet_by_id(
        db=db,
        user=current_user,
        wallet_id=wallet_id,
    )


@router.patch(
    "/{wallet_id}",
    response_model=WalletRead,
    summary="Update wallet status",
    responses={
        400: {"description": "Invalid status transition"},
        404: {"description": "Wallet not found or doesn't belong to you"},
    },
)
async def update_wallet(
    wallet_id: str,
    body: WalletUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a wallet's status.

    Valid status values:
    - **active**: Normal operations allowed.
    - **frozen**: All transactions blocked.
    - **closed**: Permanently deactivated (balance must be 0).

    Cannot close a wallet with non-zero balance.
    Cannot modify a closed wallet.
    """
    return await WalletService.update_wallet_status(
        db=db,
        user=current_user,
        wallet_id=wallet_id,
        new_status=body.status,
    )
