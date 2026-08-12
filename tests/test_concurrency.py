"""
Concurrency and invariant testing.

This test suite aggressively hammers the API to prove that our
pessimistic locking and database constraints prevent race conditions,
double-spending, and negative balances.
"""

import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.wallet.models import Wallet


@pytest.mark.asyncio
async def test_thundering_herd_p2p_transfer(client: AsyncClient, db_session):
    """
    Test that 50 concurrent requests to transfer $50 from a wallet
    that only has exactly $50 will result in exactly ONE success,
    and 49 failures (either 400 Insufficient Funds or 500 DB lock timeout).
    
    The most critical assertion is that the final balance is exactly 0
    and never goes negative.
    """
    # 1. Setup users
    await client.post(
        "/api/v1/auth/register",
        json={"email": "alice_concurrent@test.com", "password": "password123"},
    )
    
    login_a = await client.post(
        "/api/v1/auth/login",
        data={"username": "alice_concurrent@test.com", "password": "password123"}
    )
    token_a = login_a.json()["access_token"]
    user_id_a = login_a.json()["user"]["id"] if "user" in login_a.json() else None
    
    await client.post(
        "/api/v1/auth/register",
        json={"email": "bob_concurrent@test.com", "password": "password123"},
    )

    # 2. Give Alice exactly $50 (5000 cents) by modifying the DB directly
    # (Since we don't have a deposit endpoint yet)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    # Create wallet via API
    await client.post(
        "/api/v1/wallets/",
        json={"currency": "USD"},
        headers=headers_a,
    )
    
    # Inject money
    stmt = select(Wallet).where(Wallet.currency == "USD")
    result = await db_session.execute(stmt)
    alice_wallet = result.scalar_one()
    alice_wallet.balance = 5000
    
    # Create Bob's wallet directly in the database to avoid race conditions
    # during the test setup.
    from app.auth.models import User
    stmt_bob = select(User).where(User.email == "bob_concurrent@test.com")
    result_bob = await db_session.execute(stmt_bob)
    bob_user = result_bob.scalar_one()
    
    bob_wallet = Wallet(user_id=bob_user.id, currency="USD", balance=0, status="active")
    db_session.add(bob_wallet)
    
    await db_session.commit()

    # 3. The attack: 50 concurrent requests trying to steal $50
    async def make_transfer():
        return await client.post(
            "/api/v1/transfers/p2p",
            json={
                "recipient_email": "bob_concurrent@test.com",
                "amount": 5000,
                "currency": "USD",
                "description": "Concurrency attack"
            },
            headers=headers_a,
        )

    # Run all 50 requests simultaneously
    responses = await asyncio.gather(*(make_transfer() for _ in range(50)))

    # 4. Analyze results
    success_count = sum(1 for r in responses if r.status_code == 200)
    
    # Exactly ONE request should succeed
    assert success_count == 1, f"Expected 1 success, got {success_count}"

    # 5. Verify database invariants
    await db_session.refresh(alice_wallet)
    
    # Balance must never be negative!
    assert alice_wallet.balance == 0, f"Balance went negative or didn't deduct: {alice_wallet.balance}"
