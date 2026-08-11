# Digital Wallet Ledger Engine

Production-ready Digital Wallet and Ledger System built with Python, FastAPI, and PostgreSQL. It implements a robust double-entry accounting engine to guarantee zero-sum transactions, pessimistic locking for concurrency, and idempotency to prevent double-charging.

## Features

- **Double-Entry Ledger Engine**: Atomic transactions with `SELECT FOR UPDATE` locking to prevent race conditions and lost updates. Enforces `∑ credits = ∑ debits`.
- **Idempotency System**: Redis-backed `SETNX` distributed locks and 24-hour response caching for safely retrying network requests.
- **Dual Authentication**: 
  - User endpoints protected by JWT Access/Refresh tokens.
  - Merchant endpoints protected by `X-API-Key` headers (hashed with SHA-256 in the database).
- **Auto-Wallet Creation**: "Venmo-like" UX where sending money to a user automatically creates a wallet in the target currency if they don't have one.
- **Background Webhooks**: Fire-and-forget `httpx` webhooks to notify merchants of successful checkout payments.
- **Strict Data Types**: Monetary values stored as `BIGINT` (minor units like cents) to eliminate floating-point arithmetic errors.

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (via asyncpg)
- **ORM**: SQLAlchemy 2.0 + Alembic (Migrations)
- **Caching & Locks**: Redis (via redis.asyncio)
- **Validation**: Pydantic v2
- **Testing**: Pytest + HTTPX

## How to Run (Docker)

The project is fully containerized. To spin it up:

```bash
# 1. Start the services (PostgreSQL, Redis, FastAPI App)
make dev

# OR without make:
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Initial Setup (Database Migrations)

Once the containers are running, you need to generate and run the initial database schema migration:

```bash
# 1. Generate the migration script
make makemigrations
# (When prompted, enter a message like "initial schema")

# 2. Apply the migration to PostgreSQL
make migrate
```

## API Documentation

FastAPI automatically generates interactive API documentation. With the app running, visit:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Running Tests

To run the full test suite with coverage:

```bash
make test
```

## Architecture Notes

- **App Structure**: Built using a domain-driven structure (feature-first). Each domain (`auth`, `wallet`, `ledger`, `transfers`, `merchant`) has its own `models`, `schemas`, `repository`, `service`, and `routes`.
- **Ledger Entries**: `LedgerEntry` models have no `updated_at` column. They are strictly append-only. To reverse a transaction, a new compensating transaction is issued.
- **Passwords vs API Keys**: Passwords are hashed with `bcrypt` (intentionally slow). API Keys are hashed with `SHA-256` (fast) since they are highly entropic (48 random URL-safe bytes).

## License

MIT
