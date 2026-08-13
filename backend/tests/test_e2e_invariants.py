import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.wallet.models import Wallet
from app.ledger.models import Transaction, LedgerEntry

@pytest.mark.asyncio
async def test_e2e_financial_invariants(client: AsyncClient, db_session):
    """
    Test Phase 20 - Final End-to-End Test and Invariants.
    1. Register user A & B
    2. Create Wallet for A & B
    3. Deposit to A
    4. Transfer A -> B
    5. Check invariants
    6. Check Idempotency
    """
    # 1. Register A and B
    res_a = await client.post("/api/v1/auth/register", json={"email": "a_e2e@test.com", "password": "password123"})
    assert res_a.status_code == 201
    
    res_b = await client.post("/api/v1/auth/register", json={"email": "b_e2e@test.com", "password": "password123"})
    assert res_b.status_code == 201

    # Login
    login_a = await client.post("/api/v1/auth/login", data={"username": "a_e2e@test.com", "password": "password123"})
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    login_b = await client.post("/api/v1/auth/login", data={"username": "b_e2e@test.com", "password": "password123"})
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 2. Create Wallets
    wallet_a_res = await client.post("/api/v1/wallets/", json={"currency": "USD"}, headers=headers_a)
    assert wallet_a_res.status_code == 201
    wallet_a_id = wallet_a_res.json()["id"]

    wallet_b_res = await client.post("/api/v1/wallets/", json={"currency": "USD"}, headers=headers_b)
    assert wallet_b_res.status_code == 201
    wallet_b_id = wallet_b_res.json()["id"]

    # 3. Deposit (Phase 1 / Sandbox Deposit)
    deposit_res = await client.post(f"/api/v1/wallets/{wallet_a_id}/deposit", json={"amount": 100.0}, headers=headers_a)
    assert deposit_res.status_code == 200
    assert deposit_res.json()["balance"] == 10000

    # 4. Transfer A -> B
    transfer_payload = {
        "recipient_email": "b_e2e@test.com",
        "amount": 3000, # $30.00
        "currency": "USD",
        "description": "E2E Test Transfer"
    }
    transfer_res = await client.post("/api/v1/transfers/p2p", json=transfer_payload, headers=headers_a)
    assert transfer_res.status_code == 200

    # Verify Invariant 1: Wallet balances mathematically consistent
    wallet_a_check = await client.get(f"/api/v1/wallets/{wallet_a_id}", headers=headers_a)
    assert wallet_a_check.json()["balance"] == 7000 # 10000 - 3000

    wallet_b_check = await client.get(f"/api/v1/wallets/{wallet_b_id}", headers=headers_b)
    assert wallet_b_check.json()["balance"] == 3000 # 0 + 3000

    # Verify Invariant 2 & 3: Ledger entries and Zero-Sum
    # Check DB directly
    stmt = select(Transaction).where(Transaction.transaction_type == "p2p_transfer")
    txs = (await db_session.execute(stmt)).scalars().all()
    # The last tx should be ours
    tx = txs[-1]
    
    stmt_entries = select(LedgerEntry).where(LedgerEntry.transaction_id == str(tx.id))
    entries = (await db_session.execute(stmt_entries)).scalars().all()
    
    assert len(entries) == 2
    debits = sum(e.amount for e in entries if e.entry_type == "debit")
    credits = sum(e.amount for e in entries if e.entry_type == "credit")
    
    assert debits == 3000
    assert credits == 3000
    assert debits == credits # Zero sum holds

    # 6. Verify Idempotency (Invariant 5)
    idem_payload = {
        "recipient_email": "b_e2e@test.com",
        "amount": 1000,
        "currency": "USD",
        "description": "Idempotent Transfer"
    }
    idem_headers = {**headers_a, "Idempotency-Key": "test-idem-key-123"}
    
    # First call
    res1 = await client.post("/api/v1/transfers/p2p", json=idem_payload, headers=idem_headers)
    assert res1.status_code == 200
    
    # Second call - should return identical result but NOT move money again
    res2 = await client.post("/api/v1/transfers/p2p", json=idem_payload, headers=idem_headers)
    assert res2.status_code == 200
    assert res1.json() == res2.json()

    # Balance should only go down by 1000, not 2000
    wallet_a_check_2 = await client.get(f"/api/v1/wallets/{wallet_a_id}", headers=headers_a)
    assert wallet_a_check_2.json()["balance"] == 6000 # 7000 - 1000
    
    # Verify Invariant 6: Unauthorized access
    unauth_res = await client.get(f"/api/v1/wallets/{wallet_b_id}", headers=headers_a)
    assert unauth_res.status_code == 404 # Should hide existence
    
    # Verify Insufficient Funds
    fail_payload = {
        "recipient_email": "b_e2e@test.com",
        "amount": 99999999,
        "currency": "USD"
    }
    fail_res = await client.post("/api/v1/transfers/p2p", json=fail_payload, headers=headers_a)
    assert fail_res.status_code == 400
    assert "Insufficient funds" in fail_res.json()["detail"]
    
    print("All invariants successfully verified!")
