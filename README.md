# Digital Wallet & Double-Entry Ledger Engine

A full-stack digital wallet and financial ledger system built with **FastAPI**, **PostgreSQL**, **Redis**, **React**, **TypeScript**, and **Docker**. The project demonstrates how to process peer-to-peer payments with double-entry accounting, transactional integrity, concurrency control, idempotent transfers, JWT authentication, and Redis-backed rate limiting.

The stack is designed to run locally with Docker Compose for the backend and Vite for the frontend development server.

---

## Key Features

- **JWT authentication** — secure login, registration, token refresh, and protected routes
- **User registration and login** — account creation with credential validation
- **Multi-currency wallets** — create and manage wallets in different currencies
- **Add funds** — deposit funds into wallets through the ledger engine
- **Peer-to-peer transfers** — send money between users by email
- **Double-entry ledger** — every balance change is recorded as matched debit and credit entries
- **Transactional integrity** — financial operations run inside database transactions
- **Insufficient-balance protection** — transfers are rejected when funds are not available
- **Concurrency protection** — pessimistic wallet locking prevents race conditions and double spending
- **Idempotent transfers** — `Idempotency-Key` header on P2P transfers prevents duplicate charges
- **Redis-backed rate limiting** — fixed-window rate limits on authentication and API routes
- **Transaction history and ledger details** — view past movements and per-transaction ledger legs

---

## Architecture

The application follows a layered architecture from the UI through the API, service layer, and data stores:

```
React / TypeScript frontend
         ↓
FastAPI REST API
         ↓
Service layer (auth, wallet, transfer, ledger, idempotency)
         ↓
PostgreSQL + Redis
         ↓
Double-entry ledger / transactions
```

- The **frontend** provides registration, login, wallet management, transfers, and transaction detail views.
- The **FastAPI REST API** exposes versioned endpoints under `/api/v1`.
- The **service layer** enforces business rules and coordinates ledger operations.
- **PostgreSQL** stores users, wallets, transactions, ledger entries, and idempotency records.
- **Redis** backs the fixed-window rate limiter.
- The **ledger engine** is the single path for all balance changes.

### P2P Transfer Flow

A peer-to-peer transfer follows this sequence:

```
authentication
    → validation (recipient lookup, self-transfer check, wallet resolution)
    → idempotency check (optional Idempotency-Key)
    → wallet locking (SELECT FOR UPDATE, sorted to prevent deadlocks)
    → balance validation (zero-sum check and sufficient funds)
    → debit / credit ledger entries
    → database commit
```

---

## Double-Entry Ledger

Every successful transfer creates a **debit** on the sender's wallet and a corresponding **credit** on the receiver's wallet. Amounts are stored in minor units (for example, cents).

The ledger engine enforces the accounting invariant:

**Total Debits = Total Credits**

No balance is updated outside the ledger repository. Deposits, transfers, and other movements all flow through `LedgerService.execute_transaction()`, which validates zero-sum operations before committing.

---

## Idempotency

The P2P transfer endpoint (`POST /api/v1/transfers/p2p`) accepts an optional **`Idempotency-Key`** header.

How it works:

- Each idempotency key is scoped to the authenticated user.
- A **SHA-256 hash of the request payload** is stored with the key in PostgreSQL.
- **Duplicate requests** with the same key and the same payload return the previously cached response instead of executing the transfer again.
- **Same key with a different payload** is rejected with `409 Conflict`.
- The idempotency key is stored as the transaction **`reference_id`**, linking the idempotency record to the ledger transaction.

Idempotency state is persisted in PostgreSQL so it survives cache evictions and restarts.

---

## Concurrency and Transaction Safety

Concurrent transfers are handled safely using **PostgreSQL transactions** and **pessimistic wallet locking** (`SELECT FOR UPDATE`).

Before balances change, the ledger repository:

1. Sorts wallet IDs to avoid deadlocks
2. Locks the involved wallets in a deterministic order
3. Verifies sufficient funds on the locked rows
4. Inserts the transaction and ledger entries
5. Updates wallet balances inside a savepoint

If any step fails, the operation rolls back. This prevents inconsistent balances and double spending when multiple transfers target the same wallet at the same time.

The test suite includes a **thundering herd** concurrency test that fires many simultaneous transfer requests against a single wallet balance.

---

## Authentication and Rate Limiting

### JWT Authentication

- Users register and log in through `/api/v1/auth/register` and `/api/v1/auth/login`.
- The API issues JWT access tokens; refresh tokens are supported via HttpOnly cookies.
- Protected routes require a valid `Authorization: Bearer <token>` header.

### Redis-Backed Rate Limiting

Rate limiting uses a **fixed-window counter** in Redis (`rate_limit:*` keys). Clients are identified by JWT subject, API key hash, or IP address.

- **Authentication routes** — stricter limit (10 requests per minute by default)
- **Wallet, transfer, and other protected routes** — general API limit (60 requests per minute by default)

When the limit is exceeded, the API returns **`429 Too Many Requests`**.

---

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python, FastAPI, SQLAlchemy (async), Alembic |
| Database | PostgreSQL 16 |
| Cache / rate limiting | Redis 7 |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Testing | Pytest, httpx (AsyncClient) |
| Infrastructure | Docker, Docker Compose |

---

## Project Structure

```
Digital-Wallet-Ledger-Engine/
├── backend/
│   ├── alembic/                 # Database migrations
│   ├── app/
│   │   ├── auth/                # Registration, login, JWT dependencies
│   │   ├── wallet/              # Wallet CRUD and deposits
│   │   ├── transfers/           # P2P transfer orchestration
│   │   ├── ledger/              # Double-entry transaction engine
│   │   ├── idempotency/         # Idempotency key management
│   │   ├── middleware/          # Redis rate limiter
│   │   ├── merchant/            # Merchant checkout API
│   │   ├── database/            # Async engine and session
│   │   ├── cache/               # Redis client
│   │   └── main.py              # FastAPI application factory
│   ├── tests/                   # Pytest suite
│   ├── scripts/                 # Docker entrypoint and healthcheck
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                 # Pages (auth, dashboard, transfers, wallet)
│   │   ├── components/          # Layout and UI components
│   │   ├── lib/api/             # Typed API client modules
│   │   └── stores/              # Client-side auth state
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

---

## Installation / Running Locally

### Clone the repository

```bash
git clone https://github.com/agastya793/Digital-Wallet-Ledger-Engine.git
cd Digital-Wallet-Ledger-Engine
```

### Backend (Docker Compose)

```bash
cd backend
docker compose up -d
```

Run database migrations on first startup:

```bash
docker compose exec app alembic upgrade head
```

**Health check:** [http://localhost:8000/health](http://localhost:8000/health) — returns `{"status": "healthy"}` when the API is running.

**API documentation:** [http://localhost:8000/docs](http://localhost:8000/docs) — interactive Swagger UI for all endpoints.

Docker Compose also runs health checks for PostgreSQL (`pg_isready`) and Redis (`redis-cli ping`) before starting the application container.

### Frontend (Vite dev server)

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Testing

Test dependencies are defined separately from runtime dependencies in `pyproject.toml` under the `[project.optional-dependencies]` **test** extra. They are not installed in the production Docker image by default.

From the `backend` directory:

```bash
cd backend
docker compose exec app pip install -e ".[test]"
docker compose exec app python -m pytest -v
```

### Current verified result

```
6 tests
6 passed
0 failed
0 errors
0 skipped
```

The full suite was run successfully **twice** with **6/6 passing** both times.

| Test file | What it covers |
|-----------|----------------|
| `tests/test_auth.py` | Registration, duplicate email, login, invalid credentials |
| `tests/test_concurrency.py` | Thundering herd concurrent P2P transfers |
| `tests/test_e2e_invariants.py` | End-to-end flow, ledger invariants, idempotency |

---

## Verified Functionality

The following behavior has been verified locally:

- User registration
- Login
- Invalid login rejection
- Wallet creation
- Multi-currency wallets
- Add funds (deposit)
- P2P transfer
- Receiving a transfer
- Insufficient balance rejection
- Transaction history
- Double-entry ledger entries on the transaction detail view
- Idempotent P2P transfers via `Idempotency-Key`
- Backend health endpoint (`/health`)
- PostgreSQL container health (Docker Compose `pg_isready`)
- Redis container health (Docker Compose `redis-cli ping`)
- Frontend production build (`npm run build`)

---

## Example Financial Transaction

**Starting balances**

| Account | Balance |
|---------|---------|
| Sender | $1,000 |
| Receiver | $500 |

**Transfer:** $100 from sender to receiver

**Ledger entries**

| Entry | Account | Type | Amount |
|-------|---------|------|--------|
| 1 | Sender | DEBIT | $100 |
| 2 | Receiver | CREDIT | $100 |

**Final balances**

| Account | Balance |
|---------|---------|
| Sender | $900 |
| Receiver | $600 |

Total debits ($100) equal total credits ($100).

---

## Error Handling

The API returns structured error responses for common failure cases:

| Scenario | Typical response |
|----------|------------------|
| Invalid credentials | `401 Unauthorized` |
| Duplicate wallet (same currency) | `409 Conflict` |
| Invalid currency | `400 Bad Request` |
| Insufficient balance | `400 Bad Request` |
| Invalid / unknown recipient | `404 Not Found` |
| Duplicate idempotency request (same payload) | Cached prior response |
| Idempotency payload mismatch | `409 Conflict` |
| Rate limit exceeded | `429 Too Many Requests` |

---

## Engineering Highlights

This project emphasizes backend reliability and financial correctness:

- **Financial consistency** — balances change only through the ledger engine
- **Double-entry accounting** — every movement has matching debit and credit legs
- **Transactional database operations** — atomic commits with rollback on failure
- **Concurrency protection** — pessimistic locking and sorted wallet acquisition
- **Idempotency** — safe retries for P2P payments without duplicate execution
- **Redis rate limiting** — protects authentication and API endpoints from abuse
- **Async FastAPI / SQLAlchemy** — non-blocking I/O for database and cache access
- **Automated financial-invariant testing** — end-to-end and concurrency tests validate ledger rules
- **Dockerized infrastructure** — PostgreSQL, Redis, and the API run as a reproducible local stack

---

## Future Improvements

The following are **planned ideas**, not current features:

- Transaction reconciliation workflows
- Expanded concurrency and load tests
- Audit and event logging
- Observability and metrics (tracing, dashboards)
- CI/CD pipeline
- Production deployment hardening

---

## License

MIT License

---

## Author

**Shubham Thakur**

GitHub: [https://github.com/agastya793](https://github.com/agastya793)
