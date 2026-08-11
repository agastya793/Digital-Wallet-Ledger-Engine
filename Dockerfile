# =============================================================================
# Digital Wallet Ledger Engine — Dockerfile
# =============================================================================
# Multi-stage build:
#   Stage 1 (builder): Install system deps + pip packages with compilation.
#   Stage 2 (production): Copy only the compiled wheels + app code.
#
# Result: Final image ~150 MB instead of ~900 MB.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install dependencies that need compilation
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# System packages needed to compile C-extension wheels:
#   gcc         — C compiler (needed by asyncpg, bcrypt, hiredis)
#   libpq-dev   — PostgreSQL client headers (needed by asyncpg)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only the dependency manifest first.
# Docker caches this layer — if pyproject.toml hasn't changed,
# pip install is skipped on rebuild (saves 2-3 minutes).
COPY pyproject.toml README.md ./

# We create a dummy 'app' folder so hatchling can successfully build the wheel for the project.
# We then delete the project's own wheel because we only want to cache dependency wheels.
RUN mkdir app \
    && pip install --no-cache-dir --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /build/wheels . \
    && rm /build/wheels/digital_wallet_ledger_engine*.whl

# ---------------------------------------------------------------------------
# Stage 2: Production — minimal runtime image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS production

# Runtime system dependencies:
#   libpq5   — PostgreSQL client library (runtime only, no headers)
#   curl     — used by Docker HEALTHCHECK
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Security: non-root user ----
# If the container is compromised, the attacker gets `appuser` privileges,
# not root. UID 1000 is a convention that avoids conflicts with host UIDs.
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home appuser

WORKDIR /app
ENV PYTHONPATH=/app

# Copy pre-built wheels from builder stage and install them.
COPY --from=builder /build/wheels /tmp/wheels
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels /tmp/wheels/*.whl \
    && rm -rf /tmp/wheels

# Copy application code.
COPY . .

# Strip Windows carriage returns from shell scripts (belt-and-suspenders).
# Handles files downloaded as zip (not cloned via git).
RUN find . -name "*.sh" -exec sed -i 's/\r$//' {} +

# Make entrypoint executable.
RUN chmod +x scripts/docker-entrypoint.sh

# Switch to non-root user.
USER appuser

# Expose the application port.
EXPOSE 8000

# ---- Health check ----
# Docker uses this to determine container health status.
# Runs every 30s, times out after 10s, needs 3 consecutive failures.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python", "scripts/healthcheck.py"]

# ---- Entrypoint & Command ----
# Entrypoint: waits for DB, runs migrations, then exec's the CMD.
# CMD: starts uvicorn. Can be overridden at runtime.
ENTRYPOINT ["scripts/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
