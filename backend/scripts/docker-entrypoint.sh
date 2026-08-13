#!/usr/bin/env bash
# =============================================================================
# Docker Entrypoint — runs BEFORE the application starts.
# =============================================================================
# Sequence:
#   1. Wait for PostgreSQL to accept connections (retry loop)
#   2. Run Alembic database migrations (unless SKIP_MIGRATIONS=true)
#   3. exec "$@" — replace this script with the CMD (uvicorn)
#
# Why exec "$@"?
#   Makes uvicorn PID 1 inside the container, so it receives SIGTERM
#   directly from Docker. Without exec, this shell script is PID 1
#   and uvicorn never gets the signal → ungraceful shutdown.
# =============================================================================

set -euo pipefail
# -e: exit on error
# -u: treat unset variables as errors
# -o pipefail: pipe fails if any command in the pipe fails

# ---- Configuration ----
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
MAX_RETRIES="${DB_WAIT_RETRIES:-30}"
RETRY_INTERVAL="${DB_WAIT_INTERVAL:-2}"

# ---- Colors for logging ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[entrypoint]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[entrypoint]${NC} $1"; }
log_error() { echo -e "${RED}[entrypoint]${NC} $1"; }

# =========================================================================
# Step 1: Wait for PostgreSQL
# =========================================================================
# Uses Python's stdlib `socket` module — no external tools needed.
# No pg_isready, no wait-for-it, no netcat. Works in any Python image.
# =========================================================================
wait_for_db() {
    log_info "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."

    local retries=0
    until python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(3)
try:
    s.connect(('${DB_HOST}', ${DB_PORT}))
    s.close()
    exit(0)
except (ConnectionRefusedError, socket.timeout, OSError):
    exit(1)
"; do
        retries=$((retries + 1))
        if [ "$retries" -ge "$MAX_RETRIES" ]; then
            log_error "PostgreSQL not available after ${MAX_RETRIES} attempts. Exiting."
            exit 1
        fi
        log_warn "PostgreSQL not ready (attempt ${retries}/${MAX_RETRIES}). Retrying in ${RETRY_INTERVAL}s..."
        sleep "$RETRY_INTERVAL"
    done

    log_info "PostgreSQL is ready!"
}

# =========================================================================
# Step 2: Run Alembic Migrations
# =========================================================================
run_migrations() {
    if [ "${SKIP_MIGRATIONS:-false}" = "true" ]; then
        log_warn "SKIP_MIGRATIONS=true — skipping Alembic migrations."
        return
    fi

    log_info "Running Alembic migrations..."
    alembic upgrade head
    log_info "Migrations complete."
}

# =========================================================================
# Main
# =========================================================================
main() {
    wait_for_db
    run_migrations

    log_info "Starting application: $*"
    # exec replaces this script with the CMD process.
    # The CMD becomes PID 1 and receives signals directly.
    exec "$@"
}

main "$@"
