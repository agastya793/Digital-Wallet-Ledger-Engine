# Digital Wallet Ledger Engine — Progress Log

---

## Phase 1: Project Planning ✅

**Date:** 2026-08-09
**Status:** Complete

### What Was Built
- Full system architecture design (Clean Architecture: API → Service → Repository → Data)
- Complete database schema for 8 tables: `users`, `wallets`, `transactions`, `ledger_entries`, `idempotency_keys`, `refresh_tokens`, `audit_logs`, `merchant_accounts`
- Entity-Relationship diagram with all foreign keys and constraints
- Full REST API endpoint map (25+ endpoints) under `/api/v1/`
- Consistent error response schema
- Deployment architecture for free-tier (Render/Fly.io + Neon + Upstash + Grafana Cloud)
- Phase breakdown with step estimates

### Key Decisions Made
1. **Money representation:** `BIGINT` (integer minor units, e.g. paise/cents) — never float.
2. **Primary keys:** UUID v4 for all tables — prevents enumeration attacks.
3. **Balance:** Cached on `wallets.balance` (BIGINT), but `ledger_entries` is the source of truth.
4. **Locking:** Pessimistic (SELECT FOR UPDATE) for wallet balance updates; optimistic (version column) for non-critical updates.
5. **Ledger immutability:** No `updated_at` column on `ledger_entries`; no UPDATE/DELETE in repository; DB trigger to enforce.
6. **Idempotency scope:** Per-user + per-key + TTL. Same key + different payload = 409 Conflict.
7. **Auth:** JWT access token (15 min) + opaque hashed refresh token (7 days).
8. **API versioning:** URL path `/api/v1/`.
9. **Error shape:** Consistent `{ error: { code, message, details, request_id } }` across all endpoints.
10. **Deployment:** Neon (Postgres with PgBouncer), Upstash (Redis via REST), Render/Fly.io (Docker), Grafana Cloud (monitoring).

### Open TODOs
- [x] Phase 2: Create folder structure
- [ ] Set up Python project with dependencies
- [ ] Docker configuration
- [ ] Begin database model implementation

---

## Phase 2: Folder Structure ✅

**Date:** 2026-08-09
**Status:** Complete

### What Was Built
- Enterprise hybrid folder structure (feature-first domains inside a layered architecture)
- 18 domain/infrastructure packages under `app/`: `auth`, `wallet`, `ledger`, `transactions`, `transfers`, `merchant`, `admin`, `idempotency`, `audit`, `notifications`, `cache`, `middleware`, `monitoring`, `utils`, `database`, `models`, `schemas`, `api`
- Versioned API directory: `app/api/v1/`
- 5 test directories under `tests/`: `auth`, `wallet`, `ledger`, `transfers`, `concurrency`
- `alembic/versions/` for migrations
- `scripts/` for operational scripts
- `.gitignore` with Python, env, IDE, Docker, and OS exclusions
- All packages have descriptive `__init__.py` files

### Key Decisions Made
1. **Hybrid structure:** Feature modules (`auth/`, `wallet/`, `ledger/`) each contain their own `models.py`, `schemas.py`, `service.py`, `repository.py`, `routes.py` — high cohesion, low coupling.
2. **Transfers separate from Wallet:** Transfers orchestrate across wallets + ledger + transactions; mixing into wallet would create a god service.
3. **Shared packages:** `app/models/base.py` for mixins, `app/schemas/base.py` for consistent error shapes, `app/database/` for engine/session.
4. **Dedicated concurrency tests directory:** `tests/concurrency/` — the most critical tests in fintech get their own home.
5. **`__init__.py` in all packages:** Explicit over implicit for pytest discovery, IDE support, and mypy.

### Open TODOs
- [ ] Phase 3: Environment setup (`pyproject.toml`, `.env.example`, `config.py`)
- [ ] Phase 4: Docker configuration
- [ ] Phase 5: Database setup
