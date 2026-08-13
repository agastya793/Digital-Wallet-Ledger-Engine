"""
Alembic migration environment — async configuration.

This file is run by Alembic whenever you execute a migration command.
It configures:
1. The database URL (dynamically from app.config.settings).
2. The target metadata (from our SQLAlchemy models).
3. Async migration execution (using asyncpg).
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.config import settings
from app.models.base import Base

# ---- Alembic Config ----
# This is the Alembic Config object, which provides access to
# values within the alembic.ini file.
config = context.config

# Set the database URL dynamically from our Pydantic settings.
# This overrides the empty `sqlalchemy.url` in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# ---- Logging ----
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---- Target Metadata ----
# Alembic compares this metadata against the database schema
# to generate migration scripts.
# We import all models here to register them with Base.metadata.
from app.auth.models import RefreshToken, User  # noqa
from app.wallet.models import Wallet  # noqa
from app.ledger.models import LedgerEntry, Transaction  # noqa
from app.merchant.models import CheckoutSession, MerchantAccount  # noqa
from app.idempotency.models import IdempotencyKey  # noqa
from app.reconciliation.models import ReconciliationJob, ReconciliationDiscrepancy  # noqa

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL scripts without connecting to the database.
    Useful for reviewing migrations before applying them.

    Usage: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Execute migrations against a live connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode using an async engine.

    Creates an async engine from the config, connects, and runs
    migrations inside the connection context.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # NullPool: don't keep connections open after migration.
        # Migrations are one-shot — no need for a connection pool.
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations — delegates to async runner."""
    asyncio.run(run_async_migrations())


# ---- Dispatch ----
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
