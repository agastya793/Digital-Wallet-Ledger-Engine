# Digital Wallet Ledger Engine

Production-ready Digital Wallet and Ledger System. This is a full-stack monorepo consisting of a robust double-entry accounting engine (backend) and a responsive dashboard (frontend).

## System Architecture

The repository is structured into two main components:

### 1. Backend (`/backend`)
Built with Python, FastAPI, and PostgreSQL. It implements a robust double-entry accounting engine to guarantee zero-sum transactions, pessimistic locking for concurrency, and idempotency to prevent double-charging.

**Key Features:**
- **Double-Entry Ledger Engine**: Atomic transactions with `SELECT FOR UPDATE` locking to prevent race conditions.
- **Database-Level Defense-in-Depth**: Strict PostgreSQL constraints (`CHECK (balance >= 0)`).
- **Idempotency System**: Permanent idempotency keys tracked via PostgreSQL.
- **Dual Authentication**: JWT for users, `X-API-Key` for merchants.
- **Background Webhooks**: httpx webhooks for merchant checkout events.

### 2. Frontend (`/frontend`)
Built with React, Vite, TailwindCSS, and React Query. Provides a modern, responsive user interface for users to register, view balances, send money, and test merchant checkouts.

**Key Features:**
- **Authentication**: JWT-based login/register flow.
- **Dashboard**: Real-time wallet balances and transaction history.
- **Transfers**: P2P money transfers to other users by email.
- **Merchant Sandbox**: Create and test API checkout sessions.

---

## How to Run the System

You need to run both the backend and frontend to use the complete application.

### Step 1: Start the Backend (Docker)
The backend is fully containerized. Open a terminal and run:

```bash
cd backend
docker compose up -d
```

*Note: On your first run, you need to execute database migrations:*
```bash
docker compose exec app alembic upgrade head
```

### Step 2: Start the Frontend (Vite)
Open a new terminal window and run:

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` in your browser to access the application.

---

## API Documentation

FastAPI automatically generates interactive API documentation. With the backend running, visit:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Running Tests

To run the backend test suite (including the "Thundering Herd" concurrency stress test):

```bash
cd backend
docker compose exec app python -m pytest -v
```

## License

MIT
